"""
Model database.
Loads from data/models.json (static) and can be refreshed dynamically
via ModelFetcher to stay up-to-date with the latest Anthropic and Ollama models.
"""

import json
import os
from dataclasses import dataclass
from typing import List, Optional, Callable

DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "models.json"
)


@dataclass
class ClaudeAPIModel:
    id: str
    display_name: str
    tier: str
    description: str
    context_window: int
    strengths: List[str]
    recommended_for: List[str]
    min_score: int


@dataclass
class LocalModel:
    id: str
    display_name: str
    provider: str
    description: str
    vram_required_mb: int
    ram_required_gb: float
    quality: str
    speed: str
    use_case: str


def _load_static() -> dict:
    with open(os.path.abspath(DATA_PATH)) as f:
        return json.load(f)


def _to_api_model(d: dict) -> ClaudeAPIModel:
    return ClaudeAPIModel(
        id             = d.get("id", ""),
        display_name   = d.get("display_name", d.get("id", "")),
        tier           = d.get("tier", "unknown"),
        description    = d.get("description", ""),
        context_window = int(d.get("context_window", 200000)),
        strengths      = d.get("strengths", []),
        recommended_for= d.get("recommended_for", []),
        min_score      = int(d.get("min_score", 0)),
    )


def _to_local_model(d: dict) -> LocalModel:
    return LocalModel(
        id              = d.get("id", ""),
        display_name    = d.get("display_name", d.get("id", "")),
        provider        = d.get("provider", "ollama"),
        description     = d.get("description", ""),
        vram_required_mb= int(d.get("vram_required_mb", 0)),
        ram_required_gb = float(d.get("ram_required_gb", 4)),
        quality         = d.get("quality", "unknown"),
        speed           = d.get("speed", "moderate"),
        use_case        = d.get("use_case", ""),
    )


class ModelDatabase:
    """
    Holds the current set of Claude API models and local Ollama models.

    Always initialises from the static data/models.json.
    Call `refresh()` to fetch live data from Anthropic + Ollama.
    """

    def __init__(self):
        data = _load_static()
        self.claude_api_models: List[ClaudeAPIModel] = [
            _to_api_model(m) for m in data.get("claude_api_models", [])
        ]
        self.local_models: List[LocalModel] = [
            _to_local_model(m) for m in data.get("local_models", [])
        ]
        self._fetch_result = None   # most recent FetchResult, if any

    # ── Live refresh ──────────────────────────────────────────────────

    def refresh(
        self,
        api_key:     Optional[str] = None,
        force:       bool          = False,
        on_progress: Optional[Callable] = None,
    ) -> "FetchResult":
        """
        Fetch the latest models from Anthropic + Ollama and update this database.
        Returns the FetchResult for inspection.
        """
        from ..setup.model_fetcher import ModelFetcher
        result = ModelFetcher().fetch(
            api_key=api_key, force=force, on_progress=on_progress
        )
        self.apply_fetch(result)
        return result

    def apply_fetch(self, result) -> None:
        """
        Merge a FetchResult into this database in-place.
        Installed Ollama models are marked with an `_installed` badge.
        """
        self._fetch_result = result

        # Update Claude API models if the fetch returned any
        if result.claude_api_models:
            self.claude_api_models = [_to_api_model(m) for m in result.claude_api_models]

        # Build local model list: installed + library (deduplicated)
        all_local_raw = result.all_local_models()
        if all_local_raw:
            self.local_models = [_to_local_model(m) for m in all_local_raw]
        # If nothing was fetched, keep the static list

    def last_fetch_source(self) -> str:
        """'api' | 'cache' | 'static' — where the current data came from."""
        return self._fetch_result.source if self._fetch_result else "static"

    def installed_model_ids(self) -> List[str]:
        """Return IDs of models actually installed in the local Ollama instance."""
        if not self._fetch_result:
            return []
        return [m.get("id", "") for m in self._fetch_result.ollama_installed]

    # ── Queries ───────────────────────────────────────────────────────

    def get_api_model(self, model_id: str) -> Optional[ClaudeAPIModel]:
        for m in self.claude_api_models:
            if m.id == model_id:
                return m
        return None

    def get_local_model(self, model_id: str) -> Optional[LocalModel]:
        for m in self.local_models:
            if m.id == model_id:
                return m
        return None

    def compatible_local_models(self, vram_mb: int, ram_gb: float) -> List[LocalModel]:
        """Return local models that fit within the given hardware constraints."""
        compatible = []
        for m in self.local_models:
            if vram_mb > 0:
                if m.vram_required_mb <= vram_mb and m.ram_required_gb <= ram_gb:
                    compatible.append(m)
            else:
                # CPU-only: rough heuristic
                if m.ram_required_gb <= ram_gb * 0.6:
                    compatible.append(m)
        return compatible
