"""
Model database loader.
Reads data/models.json and provides typed access to model information.
"""

import json
import os
from dataclasses import dataclass
from typing import List, Optional

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


class ModelDatabase:
    def __init__(self):
        with open(os.path.abspath(DATA_PATH)) as f:
            data = json.load(f)

        self.claude_api_models: List[ClaudeAPIModel] = [
            ClaudeAPIModel(**m) for m in data["claude_api_models"]
        ]
        self.local_models: List[LocalModel] = [
            LocalModel(**m) for m in data["local_models"]
        ]

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
                # CPU-only: use RAM as the constraint (at least 2x model size)
                if m.ram_required_gb <= ram_gb * 0.6:
                    compatible.append(m)
        return compatible
