"""
Model recommendation engine.
Takes hardware specs + benchmark results and recommends the best Claude/local models.
"""

from dataclasses import dataclass
from typing import List, Optional
from .database import ClaudeAPIModel, LocalModel


@dataclass
class Recommendation:
    primary_api_model: ClaudeAPIModel
    alternative_api_model: Optional[ClaudeAPIModel]
    local_models: List[LocalModel]
    strategy: str          # "api_only", "local_capable", "local_preferred"
    reasoning: str
    tips: List[str]


class ModelRecommender:
    """
    Recommends models based on hardware tier, GPU VRAM, and RAM.

    Strategy decisions:
    - api_only:        No capable GPU or VRAM < 6 GB. Use Anthropic API.
    - local_capable:   Mid-range GPU (6–16 GB VRAM). Can run small local models.
    - local_preferred: High-end GPU (>16 GB VRAM). Local models are first-class.
    """

    def __init__(self, db=None):
        from .database import ModelDatabase
        self.db = db if db is not None else ModelDatabase()

    def recommend(
        self,
        benchmark_tier: str,
        overall_score: float,
        ram_gb: float,
        vram_mb: int,
        is_apple_silicon: bool = False,
    ) -> Recommendation:

        strategy = self._choose_strategy(vram_mb, ram_gb, is_apple_silicon)
        api_primary, api_alt = self._choose_api_models(benchmark_tier, overall_score)
        local = self._choose_local_models(vram_mb, ram_gb, is_apple_silicon, strategy)
        reasoning = self._build_reasoning(strategy, vram_mb, ram_gb, is_apple_silicon)
        tips = self._build_tips(strategy, is_apple_silicon, vram_mb, ram_gb)

        return Recommendation(
            primary_api_model=api_primary,
            alternative_api_model=api_alt,
            local_models=local,
            strategy=strategy,
            reasoning=reasoning,
            tips=tips,
        )

    # ------------------------------------------------------------------
    # Strategy
    # ------------------------------------------------------------------

    def _choose_strategy(self, vram_mb: int, ram_gb: float, apple_silicon: bool) -> str:
        # Apple Silicon has unified memory — treat system RAM as VRAM pool
        effective_vram = vram_mb
        if apple_silicon and vram_mb == 0:
            effective_vram = int(ram_gb * 1024 * 0.7)  # 70 % of RAM usable for GPU

        if effective_vram >= 16_000:
            return "local_preferred"
        if effective_vram >= 6_000:
            return "local_capable"
        return "api_only"

    # ------------------------------------------------------------------
    # API model selection
    # ------------------------------------------------------------------

    def _choose_api_models(self, tier: str, score: float):
        models = self.db.claude_api_models
        if not models:
            raise ValueError("No Claude API models available in the database.")

        # Use named fallbacks so index access never crashes on short lists
        _first  = models[0]
        _last   = models[-1]
        _second = models[1] if len(models) > 1 else _first

        sonnet = next((m for m in models if "sonnet" in m.id), _second)
        haiku  = next((m for m in models if "haiku"  in m.id), _first)
        opus   = next((m for m in models if "opus"   in m.id), _last)

        # Sonnet is always the recommended default for Claude Code
        # Haiku is offered as an alternative for speed / cost
        # Opus as alternative when the machine is very powerful (user may want best quality)
        if tier in ("ultra", "high"):
            return sonnet, opus
        return sonnet, haiku

    # ------------------------------------------------------------------
    # Local model selection
    # ------------------------------------------------------------------

    def _choose_local_models(
        self, vram_mb: int, ram_gb: float, apple_silicon: bool, strategy: str
    ) -> List[LocalModel]:
        effective_vram = vram_mb
        if apple_silicon and vram_mb == 0:
            effective_vram = int(ram_gb * 1024 * 0.7)

        if strategy == "api_only":
            return []

        compatible = self.db.compatible_local_models(effective_vram, ram_gb)
        if not compatible:
            return []

        # Sort by quality, return top-3
        quality_order = {"excellent": 5, "very good": 4, "good": 3, "fair": 2, "basic": 1}
        compatible.sort(key=lambda m: quality_order.get(m.quality, 0), reverse=True)
        return compatible[:3]

    # ------------------------------------------------------------------
    # Explanatory text
    # ------------------------------------------------------------------

    def _build_reasoning(
        self, strategy: str, vram_mb: int, ram_gb: float, apple_silicon: bool
    ) -> str:
        if apple_silicon:
            effective_gb = round(ram_gb * 0.7, 1)
            if strategy == "local_preferred":
                return (
                    f"Your Apple Silicon chip has {ram_gb} GB unified memory "
                    f"(~{effective_gb} GB available for the GPU). "
                    "You can run mid-to-large local models efficiently with Metal acceleration."
                )
            return (
                f"Your Apple Silicon machine has {ram_gb} GB unified memory. "
                "Smaller local models will work, but Claude API (Sonnet) gives better results."
            )

        vram_gb = round(vram_mb / 1024, 1) if vram_mb else 0
        if strategy == "local_preferred":
            return (
                f"You have {vram_gb} GB of GPU VRAM — enough to run large local LLMs. "
                "Local inference means zero API cost and full privacy."
            )
        if strategy == "local_capable":
            return (
                f"You have {vram_gb} GB of GPU VRAM. You can run smaller local models "
                f"(up to ~{vram_gb:.0f} GB parameter models) alongside the Claude API."
            )
        return (
            f"Your system has {ram_gb} GB RAM"
            + (f" and {vram_gb} GB VRAM" if vram_gb else " with no discrete GPU")
            + ". The Claude API is your best bet for high-quality coding assistance."
        )

    def _build_tips(
        self, strategy: str, apple_silicon: bool, vram_mb: int, ram_gb: float
    ) -> List[str]:
        tips = []
        if strategy == "api_only":
            tips.append("Use claude-3-7-sonnet-20250219 for the best quality/speed tradeoff.")
            tips.append("Switch to claude-3-5-haiku-20241022 for faster, cheaper responses.")
            tips.append("Consider upgrading to a machine with a discrete GPU to run local models.")
        if strategy == "local_capable":
            tips.append("Install Ollama to run local models: https://ollama.ai")
            tips.append("Use the Claude API for complex tasks and local models for quick queries.")
            tips.append("qwen2.5-coder is optimised for code — try it first.")
        if strategy == "local_preferred":
            tips.append("Install Ollama and pull your preferred model: `ollama pull <model>`.")
            tips.append("Use ClaudeForge Aliases to create a `claude-local` command pointing at Ollama.")
            tips.append("Keep the Claude API as a fallback for the hardest tasks.")
        if apple_silicon:
            tips.append("Ollama uses Metal acceleration automatically on Apple Silicon — no setup needed.")
        return tips
