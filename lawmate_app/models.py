from __future__ import annotations

from typing import List, Literal
from pydantic import BaseModel, Field

TrafficLight = Literal["green", "yellow", "red"]

class SourceItem(BaseModel):
    title: str = Field(..., description="Short title of a source")
    url: str
    why_relevant: str = Field(..., description="1–2 sentences why it matters")

class LawmateAnswer(BaseModel):
    traffic_light: TrafficLight
    risk_score: int = Field(..., ge=0, le=100)
    summary: str
    what_to_do_now: List[str]
    what_to_prepare: List[str]
    relevant_laws: List[str]
    important_deadlines: List[str]
    when_to_contact_lawyer: List[str]
    notes: List[str]
    sources: List[SourceItem] = Field(default_factory=list)
