"""Tests for PromptManager utility class."""

import unittest

from app.backend.utils.prompt_manager import PromptManager


class TestPromptManager(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = PromptManager()

    # --- get_infographic_prompt ---

    def test_infographic_prompt_contains_title_directive(self) -> None:
        prompt = self.manager.get_infographic_prompt(summary="Test sermon summary.")
        self.assertIn("A FRIDAY SERMON SUMMARY", prompt)

    def test_infographic_prompt_contains_creative_and_image_directive(self) -> None:
        prompt = self.manager.get_infographic_prompt(summary="Test sermon summary.")
        self.assertIn(
            "Create an infographic image for the content summarizing the content in it.",
            prompt,
        )
        self.assertIn("Be Creative.", prompt)

    def test_infographic_prompt_contains_summary(self) -> None:
        summary = "The sermon was about gratitude and patience."
        prompt = self.manager.get_infographic_prompt(summary=summary)
        self.assertIn(summary, prompt)

    def test_infographic_prompt_returns_str(self) -> None:
        result = self.manager.get_infographic_prompt(summary="Any text.")
        self.assertIsInstance(result, str)

    # --- get_concept_prompt ---

    def test_concept_prompt_contains_role_directive(self) -> None:
        prompt = self.manager.get_concept_prompt(summary="Intro to Islam.", theme=None)
        self.assertIn("Digital Content Strategist", prompt)

    def test_concept_prompt_contains_three_concepts_directive(self) -> None:
        prompt = self.manager.get_concept_prompt(summary="Intro to Islam.", theme=None)
        self.assertIn("three distinct thumbnail concepts", prompt)

    def test_concept_prompt_contains_psychological_triggers(self) -> None:
        prompt = self.manager.get_concept_prompt(summary="Intro to Islam.", theme=None)
        self.assertIn("psychological triggers", prompt)

    def test_concept_prompt_contains_required_fields(self) -> None:
        prompt = self.manager.get_concept_prompt(summary="Intro to Islam.", theme=None)
        for field in ("Visual Hook", "Design Directive", "Text Hook", "Color Theory"):
            self.assertIn(field, prompt)

    def test_concept_prompt_contains_summary(self) -> None:
        summary = "A reminder about the Day of Judgment."
        prompt = self.manager.get_concept_prompt(summary=summary, theme=None)
        self.assertIn(summary, prompt)

    def test_concept_prompt_appends_theme_when_provided(self) -> None:
        theme = "Ramadan special"
        prompt = self.manager.get_concept_prompt(
            summary="Fasting virtues.", theme=theme
        )
        self.assertIn(theme, prompt)

    def test_concept_prompt_no_theme_omits_theme_section(self) -> None:
        prompt = self.manager.get_concept_prompt(summary="Patience.", theme=None)
        self.assertNotIn("Theme:", prompt)

    def test_concept_prompt_returns_str(self) -> None:
        result = self.manager.get_concept_prompt(summary="Test.", theme=None)
        self.assertIsInstance(result, str)

    # --- get_thumbnail_prompt ---

    def test_thumbnail_prompt_contains_design_directive_instruction(self) -> None:
        concept = {"design_directive": "Bold split-screen layout with glowing borders."}
        prompt = self.manager.get_thumbnail_prompt(
            concept=concept, reference_image="ref.jpg"
        )
        self.assertIn("Design Directive", prompt)

    def test_thumbnail_prompt_contains_16_9_ratio(self) -> None:
        concept = {"design_directive": "Dark cinematic."}
        prompt = self.manager.get_thumbnail_prompt(
            concept=concept, reference_image="ref.jpg"
        )
        self.assertIn("16:9", prompt)

    def test_thumbnail_prompt_contains_islamic_compliance_directive(self) -> None:
        concept = {"design_directive": "Minimal."}
        prompt = self.manager.get_thumbnail_prompt(
            concept=concept, reference_image="ref.jpg"
        )
        self.assertIn(
            "Also to make the resulting thumbnail islamic, avoid generating eyes",
            prompt,
        )

    def test_thumbnail_prompt_contains_reference_image_path(self) -> None:
        concept = {"design_directive": "Vivid."}
        ref = "/path/to/reference.jpg"
        prompt = self.manager.get_thumbnail_prompt(concept=concept, reference_image=ref)
        self.assertIn(ref, prompt)

    def test_thumbnail_prompt_contains_design_directive_value(self) -> None:
        directive = "Neon glow on dark background."
        concept = {"design_directive": directive}
        prompt = self.manager.get_thumbnail_prompt(
            concept=concept, reference_image="ref.jpg"
        )
        self.assertIn(directive, prompt)

    def test_thumbnail_prompt_returns_str(self) -> None:
        concept = {"design_directive": "Simple layout."}
        result = self.manager.get_thumbnail_prompt(
            concept=concept, reference_image="ref.jpg"
        )
        self.assertIsInstance(result, str)

    # --- get_summary_prompt ---

    def test_summary_prompt_exact_content(self) -> None:
        prompt = self.manager.get_summary_prompt()
        self.assertIn(
            "Translate this into English and structure the content in well defined topics.",
            prompt,
        )

    def test_summary_prompt_returns_str(self) -> None:
        self.assertIsInstance(self.manager.get_summary_prompt(), str)

    # --- get_hashtags_prompt ---

    def test_hashtags_prompt_contains_topic_specific_and_youtube(self) -> None:
        prompt = self.manager.get_hashtags_prompt()
        self.assertIn("5 to 10 topic-specific hashtags", prompt)
        self.assertIn("YouTube video", prompt)

    def test_hashtags_prompt_specifies_hashtag_prefix(self) -> None:
        prompt = self.manager.get_hashtags_prompt()
        self.assertIn("prefixed with #", prompt)

    def test_hashtags_prompt_returns_str(self) -> None:
        self.assertIsInstance(self.manager.get_hashtags_prompt(), str)


if __name__ == "__main__":
    unittest.main()
