from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class DifficultyLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Resource(BaseModel):
    title: str
    url: str
    reason: str
    confidence: Confidence

    @field_validator("url")
    @classmethod
    def must_be_http(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError(f"url must be http(s): {v}")
        return v


class LevelBlock(BaseModel):
    level: DifficultyLevel
    resources: list[Resource] = Field(min_length=1)


class RoadmapContract(BaseModel):
    """Output contract the LLM's final roadmap generation must satisfy."""

    topic: str
    summary: str
    levels: list[LevelBlock]
    total_estimated_hours: float

    @model_validator(mode="after")
    def check_all_levels_present(self) -> "RoadmapContract":
        present = {block.level for block in self.levels}
        required = {DifficultyLevel.beginner, DifficultyLevel.intermediate, DifficultyLevel.advanced}
        missing = required - present
        if missing:
            raise ValueError(f"missing levels: {sorted(m.value for m in missing)}")
        return self

    @model_validator(mode="after")
    def check_low_confidence_limit(self) -> "RoadmapContract":
        low_count = sum(
            1 for block in self.levels for resource in block.resources if resource.confidence == Confidence.low
        )
        if low_count >= 3:
            raise ValueError(f"too many low-confidence resources: {low_count} (limit is < 3)")
        return self

    def validate_urls_against_allowlist(self, allowed_urls: set[str]) -> None:
        """Raise if the model hallucinated a URL that never appeared in a search Observation."""
        used = {resource.url for block in self.levels for resource in block.resources}
        hallucinated = used - allowed_urls
        if hallucinated:
            raise ValueError(f"urls not found in search observations: {sorted(hallucinated)}")


# --- API request/response schemas ---


class CurateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=200)


class CurateResponse(BaseModel):
    roadmap_id: int


class RoadmapResponse(BaseModel):
    id: int
    topic: str
    status: str
    # 'success' results satisfy RoadmapContract; 'partial' results are assembled
    # directly from collected evaluations and may omit fields like hours, so this
    # stays a loose dict rather than the strict contract.
    result: dict | None
    created_at: datetime


class ReactStepOut(BaseModel):
    step_order: int
    step_type: str
    content: str
    created_at: datetime


class RoadmapListItem(BaseModel):
    id: int
    topic: str
    status: str
    created_at: datetime
