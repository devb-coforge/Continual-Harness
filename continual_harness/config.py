from __future__ import annotations

import math
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelSettings:
    model: str
    temperature: float = 0.0
    max_tokens: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("Each role needs a model")
        if self.max_tokens is not None and (type(self.max_tokens) is not int or self.max_tokens < 1):
            raise ValueError("max_tokens must be a positive integer")
        if type(self.temperature) not in (int, float) or not math.isfinite(self.temperature) or not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be finite and between 0 and 2")


@dataclass(frozen=True)
class Config:
    actor: ModelSettings
    judge: ModelSettings
    optimizer: ModelSettings
    iterations: int = 2
    repetitions: int = 1
    concurrency: int = 4
    timeout_seconds: int = 120
    min_gain: float = 0.0
    max_regressions: int = 0
    max_strategy_chars: int = 12000
    feedback_failures: int = 6
    feedback_successes: int = 3
    max_attempts: int = 4
    retry_delay_seconds: float = 1.0

    def __post_init__(self) -> None:
        for name in ("iterations", "repetitions", "concurrency", "timeout_seconds", "max_strategy_chars", "feedback_failures", "feedback_successes", "max_attempts"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if type(self.max_regressions) is not int or self.max_regressions < 0:
            raise ValueError("max_regressions must be a nonnegative integer")
        if type(self.min_gain) not in (int, float) or not math.isfinite(self.min_gain) or not 0 <= self.min_gain <= 1:
            raise ValueError("min_gain must be finite and between 0 and 1")
        if (type(self.retry_delay_seconds) not in (int, float)
                or not math.isfinite(self.retry_delay_seconds) or self.retry_delay_seconds < 0):
            raise ValueError("retry_delay_seconds must be finite and nonnegative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        data = dict(data)
        for role in ("actor", "judge", "optimizer"):
            data[role] = ModelSettings(**data[role])
        return cls(**data)

    @classmethod
    def load(cls, path: Path) -> Config:
        with path.open("rb") as handle:
            return cls.from_dict(tomllib.load(handle))
