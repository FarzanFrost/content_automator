import unittest

from pydantic import ValidationError

from app.backend.config.settings import AppSettings
from app.backend.entities.ai_models import ConceptList, ThumbnailConcept
from app.backend.entities.project import ProjectState


class TestAIModels(unittest.TestCase):
    def test_thumbnail_concept_valid(self) -> None:
        concept = ThumbnailConcept(
            category="finance",
            visual_hook="Shocked face with falling coin chart",
            design_directive="High contrast bold text overlay",
            text_hook="Why Bitcoin Dropped 20%",
            color_theory="Red background with bright yellow text",
        )
        self.assertEqual(concept.category, "finance")
        self.assertEqual(concept.visual_hook, "Shocked face with falling coin chart")
        self.assertEqual(concept.design_directive, "High contrast bold text overlay")
        self.assertEqual(concept.text_hook, "Why Bitcoin Dropped 20%")
        self.assertEqual(concept.color_theory, "Red background with bright yellow text")

    def test_thumbnail_concept_missing_field_raises(self) -> None:
        with self.assertRaises(ValidationError):
            ThumbnailConcept(
                category="finance",
                visual_hook="Shocked face",
                design_directive="Bold",
                # missing text_hook and color_theory
            )

    def test_concept_list(self) -> None:
        concept = ThumbnailConcept(
            category="tech",
            visual_hook="Robot holding glowing core",
            design_directive="Cyberpunk glow",
            text_hook="AI Replaced Devs?",
            color_theory="Neon cyan on dark navy",
        )
        concept_list = ConceptList(concepts=[concept])
        self.assertEqual(len(concept_list.concepts), 1)
        self.assertEqual(concept_list.concepts[0].text_hook, "AI Replaced Devs?")

        # Check JSON roundtrip
        json_data = concept_list.model_dump_json()
        loaded = ConceptList.model_validate_json(json_data)
        self.assertEqual(len(loaded.concepts), 1)
        self.assertEqual(loaded.concepts[0].category, "tech")


class TestProjectState(unittest.TestCase):
    def test_project_state_defaults(self) -> None:
        state = ProjectState()
        self.assertEqual(state.project_dir, "")
        self.assertEqual(state.audio_path, "")
        self.assertEqual(state.summary_v1, "")
        self.assertEqual(state.themes, [])
        self.assertEqual(state.selected_hashtags, [])
        self.assertEqual(state.selected_infographic_path, "")

    def test_project_state_custom_values(self) -> None:
        state = ProjectState(
            project_dir="/tmp/project_1",
            audio_path="/tmp/project_1/audio.mp3",
            summary_v1="Summary content",
            themes=["finance", "investing"],
            selected_hashtags=["#money", "#crypto"],
            selected_infographic_path="/tmp/project_1/info.png",
        )
        self.assertEqual(state.project_dir, "/tmp/project_1")
        self.assertEqual(state.audio_path, "/tmp/project_1/audio.mp3")
        self.assertEqual(state.summary_v1, "Summary content")
        self.assertEqual(state.themes, ["finance", "investing"])
        self.assertEqual(state.selected_hashtags, ["#money", "#crypto"])
        self.assertEqual(state.selected_infographic_path, "/tmp/project_1/info.png")

    def test_project_state_reset(self) -> None:
        state = ProjectState(
            project_dir="/tmp/project_1",
            audio_path="/tmp/project_1/audio.mp3",
            summary_v1="Summary",
            themes=["tech"],
            selected_hashtags=["#ai"],
            selected_infographic_path="/tmp/project_1/info.png",
        )
        state.reset()
        self.assertEqual(state.project_dir, "")
        self.assertEqual(state.audio_path, "")
        self.assertEqual(state.summary_v1, "")
        self.assertEqual(state.themes, [])
        self.assertEqual(state.selected_hashtags, [])
        self.assertEqual(state.selected_infographic_path, "")


class TestAppSettings(unittest.TestCase):
    def test_app_settings_defaults(self) -> None:
        settings = AppSettings()
        self.assertEqual(settings.DEFAULT_N_INFOGRAPHICS, 3)
        self.assertIsInstance(settings.GEMINI_API_KEY, str)
        self.assertIsInstance(settings.SHORTS_BGM_PATH, str)
        self.assertIsInstance(settings.BASE_OUTPUT_DIR, str)

    def test_app_settings_custom_values(self) -> None:
        settings = AppSettings(
            GEMINI_API_KEY="test_key",
            DEFAULT_N_INFOGRAPHICS=5,
            SHORTS_BGM_PATH="/path/to/bgm.mp3",
            BASE_OUTPUT_DIR="/path/to/output",
        )
        self.assertEqual(settings.GEMINI_API_KEY, "test_key")
        self.assertEqual(settings.DEFAULT_N_INFOGRAPHICS, 5)
        self.assertEqual(settings.SHORTS_BGM_PATH, "/path/to/bgm.mp3")
        self.assertEqual(settings.BASE_OUTPUT_DIR, "/path/to/output")

    def test_app_settings_load(self) -> None:
        settings = AppSettings.load()
        self.assertIsInstance(settings, AppSettings)


if __name__ == "__main__":
    unittest.main()
