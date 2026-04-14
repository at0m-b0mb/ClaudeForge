"""
Dynamic model fetcher.

Fetches the live list of available models from:
  1. Anthropic API  (requires ANTHROPIC_API_KEY)
  2. Local Ollama   (http://localhost:11434 — if Ollama is running)
  3. Ollama Library (https://ollama.com — best-effort public API)

Results are merged with the static data/models.json and cached at
data/models_cache.json for up to CACHE_TTL_HOURS hours so the app
stays fast on subsequent launches.
"""

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional

try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

# ── Paths ─────────────────────────────────────────────────────────────────────

_HERE          = os.path.dirname(__file__)
_DATA_DIR      = os.path.abspath(os.path.join(_HERE, "..", "..", "data"))
_STATIC_PATH   = os.path.join(_DATA_DIR, "models.json")
_CACHE_PATH    = os.path.join(_DATA_DIR, "models_cache.json")

# ── API endpoints ─────────────────────────────────────────────────────────────

ANTHROPIC_MODELS_URL   = "https://api.anthropic.com/v1/models"
OLLAMA_LOCAL_URL       = "http://localhost:11434/api/tags"
OLLAMA_SEARCH_URL      = "https://ollama.com/api/search"   # undocumented but works
OLLAMA_FALLBACK_SEARCH = "https://ollama.com/search"        # HTML fallback

CACHE_TTL_HOURS = 6
REQUEST_TIMEOUT = 8     # seconds per HTTP call


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class FetchResult:
    claude_api_models: List[dict]   = field(default_factory=list)
    ollama_installed:  List[dict]   = field(default_factory=list)
    ollama_library:    List[dict]   = field(default_factory=list)
    source: str                     = "static"   # "api" | "cache" | "static"
    fetched_at: float               = 0.0
    errors: List[str]               = field(default_factory=list)

    def all_local_models(self) -> List[dict]:
        """Merge installed + library, deduplicated by id, installed first."""
        seen = set()
        result = []
        for m in self.ollama_installed + self.ollama_library:
            mid = m.get("id", "")
            if mid and mid not in seen:
                seen.add(mid)
                result.append(m)
        return result


# ── Model-shape helpers ───────────────────────────────────────────────────────

_TIER_MAP = {
    "haiku":   ("fast",     "Fastest and most cost-effective. Great for quick tasks.",
                ["speed", "cost", "everyday coding"],
                ["quick edits", "autocomplete", "low-budget setups"]),
    "sonnet":  ("balanced", "Best balance of intelligence and speed. Recommended default.",
                ["quality", "speed", "reasoning", "coding"],
                ["most projects", "complex debugging", "architecture"]),
    "opus":    ("powerful", "Most capable model. Best for complex multi-step reasoning.",
                ["intelligence", "complex reasoning", "research"],
                ["hard problems", "large codebases", "planning"]),
}

def _infer_claude_tier(model_id: str):
    for key, val in _TIER_MAP.items():
        if key in model_id:
            return val
    return ("unknown", model_id, [], [])


def _make_claude_model(raw: dict) -> dict:
    mid          = raw.get("id", "")
    display_name = raw.get("display_name", mid)
    tier, desc, strengths, rec_for = _infer_claude_tier(mid)
    return {
        "id":             mid,
        "display_name":   display_name,
        "tier":           tier,
        "description":    desc,
        "context_window": 200000,
        "strengths":      strengths,
        "recommended_for": rec_for,
        "min_score":      0,
    }


_QUALITY_BY_PARAMS = {
    range(0,   3):  ("basic",     "very fast"),
    range(3,   8):  ("fair",      "fast"),
    range(8,  16):  ("good",      "moderate"),
    range(16, 35):  ("very good", "moderate"),
    range(35, 200): ("excellent", "slow"),
}

def _quality_from_params(params_b: float):
    for rng, (q, s) in _QUALITY_BY_PARAMS.items():
        if params_b < rng.stop:
            return q, s
    return "excellent", "slow"


def _parse_param_billions(param_str: str) -> float:
    """'8B' → 8.0,  '70B' → 70.0,  '3.8b' → 3.8"""
    m = re.search(r"(\d+(?:\.\d+)?)\s*[Bb]", param_str or "")
    return float(m.group(1)) if m else 0.0


def _make_ollama_installed(raw: dict) -> dict:
    name       = raw.get("name", "")
    size_bytes = raw.get("size", 0)
    size_gb    = size_bytes / (1024 ** 3)
    vram_mb    = max(512, int(size_gb * 900))    # 90% of file size as VRAM estimate
    ram_gb     = max(4,   int(size_gb * 1.5))

    details  = raw.get("details", {})
    param_b  = _parse_param_billions(details.get("parameter_size", ""))
    quality, speed = _quality_from_params(param_b) if param_b else ("good", "moderate")

    display = name.replace(":", " ").replace("-", " ").title()
    return {
        "id":              name,
        "display_name":    display,
        "provider":        "ollama",
        "description":     f"Installed locally via Ollama. {details.get('parameter_size', '')}.",
        "vram_required_mb": vram_mb,
        "ram_required_gb":  ram_gb,
        "quality":         quality,
        "speed":           speed,
        "use_case":        "locally installed model",
        "_installed":      True,
    }


def _make_ollama_library(raw: dict) -> Optional[dict]:
    """Parse one result from the Ollama search API."""
    name = raw.get("name", "")
    if not name:
        return None
    desc    = raw.get("description", "")
    pulls   = raw.get("pulls", 0)
    tag_list = raw.get("tags", [])

    # Pick the first numeric tag as the default variant
    default_tag = next((t for t in tag_list if re.search(r"\d", t)), "latest")
    model_id = f"{name}:{default_tag}"

    # Estimate size from tag (e.g. "7b", "13b")
    param_b = _parse_param_billions(default_tag)
    if param_b == 0:
        param_b = _parse_param_billions(name)
    vram_mb = max(1000, int(param_b * 700)) if param_b else 4000
    ram_gb  = max(4,    int(param_b * 1.2)) if param_b else 8
    quality, speed = _quality_from_params(param_b) if param_b else ("good", "moderate")

    return {
        "id":              model_id,
        "display_name":    f"{name.replace('-', ' ').title()} {default_tag.upper()}",
        "provider":        "ollama",
        "description":     desc[:120] if desc else f"Popular model from Ollama library ({pulls:,} pulls).",
        "vram_required_mb": vram_mb,
        "ram_required_gb":  ram_gb,
        "quality":         quality,
        "speed":           speed,
        "use_case":        f"library model — {', '.join(tag_list[:3])} variants available",
        "_installed":      False,
    }


# ── Fetcher ───────────────────────────────────────────────────────────────────

class ModelFetcher:
    """
    Fetches the latest models from Anthropic API and Ollama.

    Usage:
        result = ModelFetcher().fetch(api_key="sk-ant-...")
        result = ModelFetcher().fetch()          # no key → skip Anthropic
        db.apply_fetch(result)                   # merge into ModelDatabase
    """

    def fetch(
        self,
        api_key:     Optional[str] = None,
        force:       bool          = False,
        on_progress: callable      = None,
    ) -> FetchResult:
        """
        Main entry-point.  Returns a FetchResult with all discovered models.
        Uses cached data if fresh enough (< CACHE_TTL_HOURS) unless `force=True`.
        """
        if not _HAS_REQUESTS:
            return self._static_result(["requests library not installed"])

        def progress(msg: str):
            if on_progress:
                on_progress(msg)

        # ── Cache check ───────────────────────────────────────────────
        if not force:
            cached = self._load_cache()
            if cached:
                progress("Using cached model data.")
                return cached

        result = FetchResult(fetched_at=time.time(), source="api")

        # ── 1. Anthropic API models ───────────────────────────────────
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if key:
            progress("Fetching Claude models from Anthropic API…")
            try:
                resp = _requests.get(
                    ANTHROPIC_MODELS_URL,
                    headers={
                        "x-api-key":          key,
                        "anthropic-version":  "2023-06-01",
                    },
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                raw_models = resp.json().get("data", [])
                result.claude_api_models = [
                    _make_claude_model(m)
                    for m in raw_models
                    if m.get("type") == "model"
                ]
                progress(f"  Found {len(result.claude_api_models)} Claude models.")
            except Exception as exc:
                result.errors.append(f"Anthropic API: {exc}")
                progress(f"  Anthropic fetch failed: {exc}")
        else:
            progress("No API key — skipping Anthropic model fetch.")

        # ── 2. Local Ollama models ────────────────────────────────────
        progress("Checking local Ollama installation…")
        try:
            resp = _requests.get(OLLAMA_LOCAL_URL, timeout=3)
            resp.raise_for_status()
            models_raw = resp.json().get("models", [])
            result.ollama_installed = [_make_ollama_installed(m) for m in models_raw]
            progress(f"  Found {len(result.ollama_installed)} installed Ollama models.")
        except Exception as exc:
            result.errors.append(f"Ollama local: {exc}")
            progress("  Ollama not running or not installed.")

        # ── 3. Ollama library (popular models) ────────────────────────
        progress("Fetching popular models from Ollama library…")
        try:
            resp = _requests.get(
                OLLAMA_SEARCH_URL,
                params={"q": "", "sortBy": "featured", "limit": 30},
                headers={"Accept": "application/json"},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            items = resp.json() if isinstance(resp.json(), list) else resp.json().get("models", [])
            parsed = [_make_ollama_library(m) for m in items]
            result.ollama_library = [m for m in parsed if m]
            progress(f"  Found {len(result.ollama_library)} library models.")
        except Exception as exc:
            result.errors.append(f"Ollama library: {exc}")
            progress("  Could not reach Ollama library — using built-in catalog.")

        # ── Fallback: fill in any empty list from static data ─────────
        static = self._load_static()
        if not result.claude_api_models:
            result.claude_api_models = static.get("claude_api_models", [])
        if not result.ollama_library and not result.ollama_installed:
            result.ollama_library = static.get("local_models", [])

        # ── Save cache ────────────────────────────────────────────────
        self._save_cache(result)
        return result

    # ── Cache helpers ─────────────────────────────────────────────────

    def _load_cache(self) -> Optional[FetchResult]:
        if not os.path.isfile(_CACHE_PATH):
            return None
        try:
            with open(_CACHE_PATH) as f:
                data = json.load(f)
            age_hours = (time.time() - data.get("fetched_at", 0)) / 3600
            if age_hours > CACHE_TTL_HOURS:
                return None
            return FetchResult(
                claude_api_models = data.get("claude_api_models", []),
                ollama_installed  = data.get("ollama_installed",  []),
                ollama_library    = data.get("ollama_library",    []),
                source     = "cache",
                fetched_at = data.get("fetched_at", 0),
                errors     = [],
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def _save_cache(self, result: FetchResult):
        os.makedirs(_DATA_DIR, exist_ok=True)
        data = {
            "claude_api_models": result.claude_api_models,
            "ollama_installed":  result.ollama_installed,
            "ollama_library":    result.ollama_library,
            "fetched_at":        result.fetched_at,
        }
        with open(_CACHE_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def _load_static(self) -> dict:
        try:
            with open(_STATIC_PATH) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _static_result(self, errors: List[str]) -> FetchResult:
        static = self._load_static()
        return FetchResult(
            claude_api_models = static.get("claude_api_models", []),
            ollama_library    = static.get("local_models", []),
            source = "static",
            errors = errors,
        )

    def cache_age_minutes(self) -> Optional[float]:
        """Return age of the cache in minutes, or None if no cache."""
        if not os.path.isfile(_CACHE_PATH):
            return None
        try:
            with open(_CACHE_PATH) as f:
                data = json.load(f)
            return (time.time() - data.get("fetched_at", 0)) / 60
        except Exception:
            return None
