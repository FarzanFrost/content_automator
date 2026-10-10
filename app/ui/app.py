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
    ) -> Tuple[str, Any, List[str], ProjectState, str]:
        """Execute Phase 1 processing and populate review UI components."""
        current_state = state if state is not None else ProjectState()

        cleaned_link = drive_link.strip() if drive_link else ""
        if not cleaned_link:
            return (
                "",
                gr.update(choices=[], value=[]),
                [],
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
            placeholders,
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

    def _extract_path_from_event(self, evt: gr.SelectData) -> str:
        """Extract file path string from a Gradio SelectData event payload."""
        val = getattr(evt, "value", None)
        if isinstance(val, dict):
            img = val.get("image")
            if isinstance(img, dict):
                return str(img.get("path") or "")
            if isinstance(img, str):
                return img
            caption = val.get("caption")
            if caption:
                return str(caption)
        elif isinstance(val, str):
            return val
        elif isinstance(val, (list, tuple)) and val:
            return str(val[0])
        return ""

    def on_select_infographic(
        self,
        evt: gr.SelectData,
        state: Optional[ProjectState] = None,
    ) -> Tuple[str, ProjectState]:
        """Handle infographic selection from gallery and update project state."""
        current_state = state if state is not None else ProjectState()
        selected_path = self._extract_path_from_event(evt)
        current_state.selected_infographic_path = selected_path
        return f"Selected infographic: {selected_path}", current_state

    async def on_confirm_infographic(
        self,
        state: Optional[ProjectState] = None,
    ) -> Tuple[
        List[str], Optional[str], Optional[str], Optional[str], str, ProjectState
    ]:
        """Trigger Phase 2 processing and yield thumbnails, final video, shorts, and status."""
        current_state = state if state is not None else ProjectState()

        if not current_state.selected_infographic_path:
            return (
                [],
                None,
                None,
                None,
                "Error: Please select an infographic before confirming.",
                current_state,
            )

        assets = await self.service.phase_2_process(current_state)

        # Assets layout: [*thumbnails, final_video_path, shorts_video_path, shorts_thumb_path]
        if len(assets) >= 3:
            thumbnails = assets[:-3]
            final_video_path = assets[-3]
            shorts_video_path = assets[-2]
            shorts_thumb_path = assets[-1]
        else:
            thumbnails = []
            final_video_path = None
            shorts_video_path = None
            shorts_thumb_path = None

        status_msg = (
            f"Phase 2 processing complete. Assets generated in project folder: "
            f"'{current_state.project_dir}'. All deliverables are ready in your local "
            f"folder for manual YouTube upload."
        )

        return (
            thumbnails,
            final_video_path,
            shorts_video_path,
            shorts_thumb_path,
            status_msg,
            current_state,
        )

    def on_select_thumbnail(
        self,
        evt: gr.SelectData,
        state: Optional[ProjectState] = None,
    ) -> Tuple[str, ProjectState]:
        """Handle final thumbnail selection and update project state."""
        current_state = state if state is not None else ProjectState()
        selected_path = self._extract_path_from_event(evt)
        current_state.selected_thumbnail_path = selected_path
        return f"Selected final thumbnail: {selected_path}", current_state

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
                        summary_status_markdown = gr.Markdown()

                    with gr.Accordion("Step 3: Infographic Selection", open=True):
                        infographics_gallery = gr.Gallery(
                            label="Generated Infographics (Select 1)",
                            allow_preview=False,
                            columns=3,
                        )
                        confirm_infographic_btn = gr.Button(
                            "Confirm Infographic", variant="primary"
                        )
                        infographic_status_markdown = gr.Markdown()

                    with gr.Accordion("Step 4: Thumbnail Selection", open=True):
                        thumbnails_gallery = gr.Gallery(
                            label="Generated Thumbnails (Select 1 Final)",
                            allow_preview=False,
                            columns=3,
                        )
                        thumbnail_status_markdown = gr.Markdown()

                    with gr.Accordion("Step 5: Final Outputs", open=True):
                        with gr.Row():
                            final_video_player = gr.Video(label="Final Video (16:9)")
                            shorts_video_player = gr.Video(
                                label="Shorts Video Fancy (9:16)"
                            )
                            shorts_thumb_display = gr.Image(
                                label="Shorts Thumbnail (9:16)"
                            )
                        final_outputs_status_markdown = gr.Markdown()

                    # Event bindings
                    phase1_btn.click(
                        fn=self.on_start_phase_1,
                        inputs=[drive_link_input, themes_input, session_state],
                        outputs=[
                            summary_textbox,
                            hashtags_checkbox,
                            infographics_gallery,
                            session_state,
                            summary_status_markdown,
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
                        outputs=[summary_status_markdown, session_state],
                    )

                    infographics_gallery.select(
                        fn=self.on_select_infographic,
                        inputs=[session_state],
                        outputs=[infographic_status_markdown, session_state],
                    )

                    confirm_infographic_btn.click(
                        fn=self.on_confirm_infographic,
                        inputs=[session_state],
                        outputs=[
                            thumbnails_gallery,
                            final_video_player,
                            shorts_video_player,
                            shorts_thumb_display,
                            final_outputs_status_markdown,
                            session_state,
                        ],
                    )

                    thumbnails_gallery.select(
                        fn=self.on_select_thumbnail,
                        inputs=[session_state],
                        outputs=[thumbnail_status_markdown, session_state],
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
                    gr.Textbox(
                        label="Resources Directory",
                        value=settings.RESOURCES_DIR,
                        interactive=False,
                    )

        return demo
