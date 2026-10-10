"""PromptManager: factory class for structured AI prompt strings."""

from typing import Optional


class PromptManager:
    """Produces formatted prompt strings for Gemini image and concept generation."""

    def get_infographic_prompt(self, summary: str) -> str:
        """Return an Imagen 3 prompt for a sermon infographic image.

        Args:
            summary: Sermon summary text to embed in the prompt.

        Returns:
            Fully formatted prompt string.
        """
        return (
            "Create an infographic image (16:9 ratio) for the content summarizing the content in it. "
            "Be Creative. "
            "The title on top of the image must be 'A FRIDAY SERMON SUMMARY'.\n\n"
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
            "Act as a Master Digital Content Strategist with 15 years of experience in YouTube viral growth. "
            "Your task is to develop three distinct thumbnail concepts that prioritize different psychological triggers: "
            "1) A Curiosity Gap concept, 2) An Emotional Contagion concept, and 3) A Visual Anomaly/Value Comparison concept.\n\n"
            "For each concept, provide:\n"
            "The Visual Hook: A one-sentence explanation of what will stop the scroll.\n"
            "The Design Directive: A detailed 100-word paragraph describing the Subject, Background, Lighting, and Composition.\n"
            "The Text Hook: 1–3 words of impactful text with font and color recommendations.\n"
            "The Color Theory: Explain how the palette will stand out in the YouTube feed.\n\n"
            "Input Data:\n"
            "Niche: Islamic Videos\n"
            "Title: A FRIDAY SERMON SUMMARY\n"
            f"Summary: {summary}"
        )
        if theme:
            base += f"\nTheme: {theme}"
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
            "Also to make the resulting thumbnail islamic, avoid generating eyes, and make thumbnail similar "
            "to given image while following the below given directive.\n\n"
            f"Design Directive:\n{directive}\n\n"
            f"Reference Image: {reference_image}"
        )

    def get_summary_prompt(self) -> str:
        """Return prompt asking NotebookLM to translate into English and structure in topics.

        Returns:
            Fully formatted prompt string.
        """
        return "Translate this into English and structure the content in well defined topics."

    def get_hashtags_prompt(self) -> str:
        """Return prompt asking NotebookLM for 5 to 10 topic-specific YouTube hashtags.

        Returns:
            Fully formatted prompt string.
        """
        return (
            "Provide me with 5 to 10 topic-specific hashtags that I can use to upload "
            "this as a YouTube video. Output each hashtag prefixed with # separated by spaces."
        )
