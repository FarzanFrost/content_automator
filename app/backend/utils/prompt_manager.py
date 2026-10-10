"""PromptManager: factory class for structured AI prompt strings."""

from typing import Optional


class PromptManager:
    """Produces formatted prompt strings for Gemini image and concept generation."""

    def get_infographic_prompt(self, summary: str) -> str:
        """Return an Imagen 3 prompt for a 16:9 sermon infographic.

        Args:
            summary: Sermon summary text to embed in the prompt.

        Returns:
            Fully formatted prompt string.
        """
        return (
            "Create an infographic summarizing this content. "
            "16:9 ratio. "
            "Be creative. "
            "The title on top MUST be 'A FRIDAY SERMON SUMMARY'.\n\n"
            f"Content:\n{summary}"
        )

    def get_concept_prompt(self, summary: str, theme: Optional[str] = None) -> str:
        """Return a Gemini prompt requesting 3 structured thumbnail concepts.

        Args:
            summary: Sermon or content summary to analyze.
            theme: Optional creative theme to append to the prompt.

        Returns:
            Fully formatted prompt string.
        """
        base = (
            "Act as a Digital Content Strategist. "
            "Develop 3 distinct thumbnail concepts prioritizing psychological triggers "
            "that maximize click-through rate for Islamic educational content.\n\n"
            "For each concept provide:\n"
            "- Visual Hook: The primary focal element that arrests attention.\n"
            "- Design Directive: Specific layout, composition, and styling instructions.\n"
            "- Text Hook: A high-impact text overlay optimized for emotional resonance.\n"
            "- Color Theory: Palette selection with psychological framing rationale.\n\n"
            f"Content Summary:\n{summary}"
        )
        if theme is not None:
            base += f"\n\nTheme: {theme}"
        return base

    def get_thumbnail_prompt(self, concept: dict, reference_image: str) -> str:
        """Return an Imagen 3 prompt for a YouTube thumbnail from a concept dict.

        Args:
            concept: Dict containing at minimum a 'design_directive' key.
            reference_image: File path or URL of the style reference image.

        Returns:
            Fully formatted prompt string.
        """
        directive = concept.get("design_directive", "")
        return (
            "Using the Design Directive provided, generate a professional 16:9 YouTube thumbnail. "
            "To ensure Islamic compliance, avoid generating eyes. "
            "Match the style of the provided reference image.\n\n"
            f"Design Directive:\n{directive}\n\n"
            f"Reference Image: {reference_image}"
        )
