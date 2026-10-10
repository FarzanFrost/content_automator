"""Structured AI output models for Gemini API."""

from typing import List

from pydantic import BaseModel, Field


class ThumbnailConcept(BaseModel):
    """Concept model representing structured thumbnail generation directives."""

    category: str = Field(..., description="Content category for the concept")
    visual_hook: str = Field(..., description="Focal visual hook element")
    design_directive: str = Field(
        ..., description="Directives for layout and composition"
    )
    text_hook: str = Field(..., description="High-impact text overlay hook")
    color_theory: str = Field(
        ..., description="Color palette and psychological framing"
    )


class ConceptList(BaseModel):
    """Container holding a collection of thumbnail concepts."""

    concepts: List[ThumbnailConcept] = Field(
        default_factory=list,
        description="List of structured thumbnail concepts",
    )
