"""Class-based Gradio UI for Content Automator."""

from typing import Any, List, Optional, Tuple

import gradio as gr

from app.backend.config.settings import AppSettings
from app.backend.entities.project import ProjectState
from app.backend.repositories.file_repo import FileRepo
from app.backend.services.automation_service import AutomationService


class ContentAutomatorUI:
    """Class-based Gradio interface orchestrating content automation workflows."""

    def __init__(
        self,
        service: Optional[AutomationService] = None,
        file_repo: Optional[FileRepo] = None,
    ) -> None:
        """Initialize ContentAutomatorUI with service and repository dependencies."""
        self._service = service
        self._file_repo = file_repo

    @property
    def service(self) -> AutomationService:
        """Return injected or lazy-initialized AutomationService instance."""
        if self._service is None:
            self._service = AutomationService()
        return self._service

    @property
    def file_repo(self) -> FileRepo:
        """Return injected or lazy-initialized FileRepo instance."""
        if self._file_repo is None:
            self._file_repo = FileRepo()
        return self._file_repo

    async def on_start_phase_1(
        self,
        drive_link: str,
        themes_str: str,
        state: Optional[ProjectState] = None,
    ) -> Tuple[str, Any, ProjectState, str]:
        """Execute Phase 1 processing and populate review UI components."""
        current_state = state if state is not None else ProjectState()

        cleaned_link = drive_link.strip() if drive_link else ""
        if not cleaned_link:
            return (
                "",
                gr.update(choices=[], value=[]),
                current_state,
                "Error: Google Drive Link is required.",
            )

        themes = [t.strip() for t in themes_str.split(",") if t.strip()]

        new_state, placeholders = await self.service.phase_1_process(
            cleaned_link, themes, n_infographics=3
        )

        hashtag_choices = list(new_state.selected_hashtags)
        selected_default = hashtag_choices[:2]
        new_state.selected_hashtags = selected_default

        status_msg = (
            f"Complete: Phase 1 processed {len(placeholders)} infographics. "
            f"Project initialized at {new_state.project_dir}"
        )

        return (
            new_state.summary_v1,
            gr.update(choices=hashtag_choices, value=selected_default),
            new_state,
            status_msg,
        )

    def on_hashtag_change(
        self,
        selected: Optional[List[str]],
        state: Optional[ProjectState] = None,
    ) -> Tuple[Any, ProjectState]:
        """Enforce maximum of 2 hashtag selections."""
        current_state = state if state is not None else ProjectState()
        selected_list = selected or []

        if len(selected_list) > 2:
            selected_list = selected_list[:2]

        current_state.selected_hashtags = list(selected_list)
        return gr.update(value=selected_list), current_state

    def on_save_edited_summary(
        self,
        summary_text: str,
        state: Optional[ProjectState] = None,
    ) -> Tuple[str, ProjectState]:
        """Save edited summary markdown version v2_edited.md into project directory."""
        current_state = state if state is not None else ProjectState()

        if not current_state.project_dir:
            return "Error: No active project directory found.", current_state

        saved_path = self.file_repo.save_text_version(
            summary_text, "v2_edited.md", current_state.project_dir
        )
        return f"Saved edited summary to {saved_path}", current_state

    def build_ui(self) -> gr.Blocks:
        """Construct and bind Gradio Blocks application layout."""
        with gr.Blocks(title="Content Automator") as demo:
            session_state = gr.State(value=ProjectState())

            with gr.Tabs():
                with gr.Tab("Jummah Automation"):
                    with gr.Accordion("Step 1: Init", open=True):
                        drive_link_input = gr.Textbox(
                            label="Google Drive Link",
                            placeholder="https://drive.google.com/file/d/...",
                        )
                        themes_input = gr.Textbox(
                            label="Themes (comma-separated)",
                            placeholder="faith, patience, community",
                        )
                        phase1_btn = gr.Button(
                            "Start Phase 1 Processing", variant="primary"
                        )

                    with gr.Accordion("Step 2: Text Review", open=True):
                        summary_textbox = gr.Textbox(
                            label="Generated Summary",
                            interactive=True,
                            lines=12,
                        )
                        hashtags_checkbox = gr.CheckboxGroup(
                            label="Hashtags (Select up to 2)",
                            choices=[],
                        )
                        save_summary_btn = gr.Button(
                            "Save Edited Summary", variant="secondary"
                        )
                        status_markdown = gr.Markdown()

                    phase1_btn.click(
                        fn=self.on_start_phase_1,
                        inputs=[drive_link_input, themes_input, session_state],
                        outputs=[
                            summary_textbox,
                            hashtags_checkbox,
                            session_state,
                            status_markdown,
                        ],
                    )

                    hashtags_checkbox.change(
                        fn=self.on_hashtag_change,
                        inputs=[hashtags_checkbox, session_state],
                        outputs=[hashtags_checkbox, session_state],
                    )

                    save_summary_btn.click(
                        fn=self.on_save_edited_summary,
                        inputs=[summary_textbox, session_state],
                        outputs=[status_markdown, session_state],
                    )

                with gr.Tab("Settings"):
                    gr.Markdown("### Application Configuration")
                    settings = AppSettings.load()
                    gr.Textbox(
                        label="Base Output Directory",
                        value=settings.BASE_OUTPUT_DIR,
                        interactive=False,
                    )
                    gr.Textbox(
                        label="Default Infographics Count",
                        value=str(settings.DEFAULT_N_INFOGRAPHICS),
                        interactive=False,
                    )
                    gr.Textbox(
                        label="Shorts BGM Path",
                        value=settings.SHORTS_BGM_PATH,
                        interactive=False,
                    )

        return demo
