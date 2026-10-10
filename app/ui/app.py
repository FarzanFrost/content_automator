import asyncio
from pathlib import Path
from typing import Any, List, Optional, Tuple

import gradio as gr

from app.backend.config.settings import AppSettings
from app.backend.entities.project import ProjectState
from app.backend.repositories.file_repo import FileRepo
from app.backend.services.automation_service import AutomationService
from app.backend.services.notebooklm_auth_service import NotebookLMAuthService


FINAL_VIDEO_HASHTAG = "#IslamicReminder"
SHORT_VIDEO_HASHTAG = "#IslamicShorts"
COMMON_HASHTAG = "#SeekLightWithZuFa"
DISCLAIMER = (
    "Disclaimer: AI-assisted English summary and infographics. Minor errors are possible."
)
DESCRIPTION_NEWLINES_COUNT = 7


def calculate_character_count(
    summary: Optional[str] = None,
    hashtags: Optional[List[str]] = None,
) -> int:
    """Calculate character count including summary, hashtags, common tags, disclaimer, and newlines."""
    summary_len = len(summary) if summary is not None else 0
    tag_list = hashtags or []
    tag1_len = len(tag_list[0]) if len(tag_list) > 0 else 0
    tag2_len = len(tag_list[1]) if len(tag_list) > 1 else 0
    max_tag_len = max(len(FINAL_VIDEO_HASHTAG), len(SHORT_VIDEO_HASHTAG))
    return (
        summary_len
        + tag1_len
        + tag2_len
        + max_tag_len
        + len(COMMON_HASHTAG)
        + len(DISCLAIMER)
        + DESCRIPTION_NEWLINES_COUNT
    )


class ContentAutomatorUI:
    """Class-based Gradio interface orchestrating content automation workflows."""

    def __init__(
        self,
        service: Optional[AutomationService] = None,
        file_repo: Optional[FileRepo] = None,
        auth_service: Optional[NotebookLMAuthService] = None,
    ) -> None:
        """Initialize ContentAutomatorUI with service and repository dependencies."""
        self._service = service
        self._file_repo = file_repo
        self._auth_service = auth_service

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

    @property
    def auth_service(self) -> NotebookLMAuthService:
        """Return injected or lazy-initialized NotebookLMAuthService instance."""
        if self._auth_service is None:
            self._auth_service = NotebookLMAuthService()
        return self._auth_service

    async def on_start_notebooklm(
        self,
        drive_link: str,
        themes_str: str,
        state: Optional[ProjectState] = None,
    ) -> Tuple[str, Any, ProjectState, str]:
        """Execute audio ingestion and NotebookLM processing (summary, hashtags)."""
        current_state = state if state is not None else ProjectState()

        cleaned_link = drive_link.strip() if drive_link else ""
        if not cleaned_link:
            return (
                "",
                gr.update(choices=[], value=[]),
                current_state,
                "Error: Google Drive Link is required.",
            )

        if not self.auth_service.is_authenticated():
            return (
                "",
                gr.update(choices=[], value=[]),
                current_state,
                "Error: NotebookLM is not authenticated. Please click 'Login to NotebookLM' below to connect your Google account.",
            )

        themes = [t.strip() for t in themes_str.split(",") if t.strip()]

        new_state = await self.service.generate_notebooklm_artifacts(
            cleaned_link, themes
        )

        hashtag_choices = list(new_state.selected_hashtags)
        selected_default = hashtag_choices[:2]
        new_state.selected_hashtags = selected_default

        status_msg = (
            f"Complete: NotebookLM summary and hashtags generated. "
            f"Project initialized at {new_state.project_dir}"
        )

        return (
            new_state.summary_v1,
            gr.update(choices=hashtag_choices, value=selected_default),
            new_state,
            status_msg,
        )

    async def on_generate_infographics(
        self,
        state: Optional[ProjectState] = None,
    ) -> Tuple[List[str], ProjectState, str]:
        """Generate infographics automatically without user intervention."""
        current_state = state if state is not None else ProjectState()

        if not current_state.project_dir or not current_state.summary_v1:
            return [], current_state, "Error: Project directory or summary missing."

        infographics = await self.service.generate_infographics(
            current_state, n_infographics=3
        )

        status_msg = f"Complete: Generated {len(infographics)} infographics."
        return infographics, current_state, status_msg

    def on_click_confirm_infographic(
        self, state: Optional[ProjectState] = None
    ) -> Tuple[Any, str]:
        """Disable button upon valid infographic confirmation or show error."""
        current_state = state if state is not None else ProjectState()
        if not current_state.selected_infographic_path:
            return (
                gr.update(interactive=True),
                "Error: Please select an infographic before confirming.",
            )
        return (
            gr.update(interactive=False),
            "Infographic confirmed. Generating deliverables...",
        )

    async def on_create_final_video(
        self, state: Optional[ProjectState] = None
    ) -> Tuple[Optional[str], str]:
        """Independently generate 16:9 final video."""
        current_state = state if state is not None else ProjectState()
        if not current_state.selected_infographic_path:
            return None, "Error: Infographic not selected."
        video_path = await self.service.create_final_video(current_state)
        return video_path, f"Final video rendered: {video_path}"

    async def on_create_short_video(
        self, state: Optional[ProjectState] = None
    ) -> Tuple[Optional[str], str]:
        """Independently generate 9:16 shorts video."""
        current_state = state if state is not None else ProjectState()
        if not current_state.selected_infographic_path:
            return None, "Error: Infographic not selected."
        short_path = await self.service.create_short_video(current_state)
        return short_path, f"Shorts video rendered: {short_path}"

    async def on_generate_thumbnails(
        self, state: Optional[ProjectState] = None
    ) -> Tuple[List[str], str]:
        """Independently generate thumbnail concepts and images."""
        current_state = state if state is not None else ProjectState()
        if not current_state.selected_infographic_path:
            return [], "Error: Infographic not selected."
        thumbnails = await self.service.generate_thumbnails(current_state)
        return (
            thumbnails,
            f"Thumbnails generated ({len(thumbnails)}). Please select 1 final thumbnail below.",
        )

    async def on_confirm_thumbnail(
        self, state: Optional[ProjectState] = None
    ) -> Tuple[Optional[str], Any, str]:
        """Generate 9:16 short thumbnail for the user's selected 16:9 thumbnail."""
        current_state = state if state is not None else ProjectState()
        if not current_state.selected_thumbnail_path:
            return (
                None,
                gr.update(interactive=True),
                "Error: Please select a thumbnail before confirming.",
            )
        short_thumb_path = await self.service.create_short_thumbnail(current_state)
        return (
            short_thumb_path,
            gr.update(interactive=False),
            f"Shorts thumbnail created from selected thumbnail: {short_thumb_path}",
        )

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

        if not self.auth_service.is_authenticated():
            return (
                "",
                gr.update(choices=[], value=[]),
                [],
                current_state,
                "Error: NotebookLM is not authenticated. Please click 'Login to NotebookLM' below to connect your Google account.",
            )

        themes = [t.strip() for t in themes_str.split(",") if t.strip()]

        new_state, placeholders = await self.service.phase_1_process(
            cleaned_link, themes, n_infographics=3
        )

        bg_tasks = getattr(self.service, "_background_tasks", None)
        if bg_tasks:
            await asyncio.gather(*list(bg_tasks), return_exceptions=True)

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
        summary_text: Optional[Any] = None,
        state: Optional[ProjectState] = None,
    ) -> Tuple[Any, ProjectState, str]:
        """Enforce maximum of 2 hashtag selections and recalculate character count."""
        if isinstance(summary_text, ProjectState):
            state = summary_text
            summary_text = ""
        current_state = state if state is not None else ProjectState()
        selected_list = selected or []

        if len(selected_list) > 2:
            selected_list = selected_list[:2]

        current_state.selected_hashtags = list(selected_list)
        count_str = self.on_summary_change(
            str(summary_text) if summary_text is not None else "",
            current_state.selected_hashtags,
        )
        return gr.update(value=selected_list), current_state, count_str

    def on_summary_change(
        self,
        text: Optional[str] = None,
        hashtags: Optional[List[str]] = None,
    ) -> str:
        """Return formatted character count string for summary and selected hashtags."""
        count = calculate_character_count(text, hashtags)
        return f"Character count: {count}"

    def on_save_edited_summary(
        self,
        summary_text: str,
        state: Optional[ProjectState] = None,
    ) -> Tuple[str, ProjectState]:
        """Save edited summary markdown versions into project directory."""
        current_state = state if state is not None else ProjectState()

        if not current_state.project_dir:
            return "Error: No active project directory found.", current_state

        filename = (
            Path(current_state.audio_path).name if current_state.audio_path else ""
        )
        selected_tags = current_state.selected_hashtags or []
        tag1 = selected_tags[0] if len(selected_tags) > 0 else ""
        tag2 = selected_tags[1] if len(selected_tags) > 1 else ""

        final_desc = (
            f"{filename}\n"
            f"{FINAL_VIDEO_HASHTAG}\n"
            f"{tag1}\n"
            f"{tag2}\n"
            f"{COMMON_HASHTAG}\n\n"
            f"{summary_text}\n\n"
            f"{DISCLAIMER}"
        )

        short_desc = (
            f"{filename}\n"
            f"{SHORT_VIDEO_HASHTAG}\n"
            f"{tag1}\n"
            f"{tag2}\n"
            f"{COMMON_HASHTAG}\n\n"
            f"{summary_text}\n\n"
            f"{DISCLAIMER}"
        )

        self.file_repo.save_text_version(
            final_desc, "final_video_description.md", current_state.project_dir
        )
        self.file_repo.save_text_version(
            short_desc, "short_video_description.md", current_state.project_dir
        )

        return (
            f"Saved final and short video descriptions to {current_state.project_dir}",
            current_state,
        )

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
        if current_state.project_dir and selected_path:
            filename = Path(selected_path).name
            canonical_path = Path(current_state.project_dir) / "infographics" / filename
            if canonical_path.exists():
                selected_path = str(canonical_path.resolve())
            elif getattr(evt, "index", None) is not None:
                idx = evt.index
                if isinstance(idx, (int, float)):
                    indexed_path = (
                        Path(current_state.project_dir)
                        / "infographics"
                        / f"infographic_{int(idx) + 1}.png"
                    )
                    if indexed_path.exists():
                        selected_path = str(indexed_path.resolve())
        current_state.selected_infographic_path = selected_path
        return f"Selected infographic: {selected_path}", current_state

    async def on_confirm_infographic(
        self,
        state: Optional[ProjectState] = None,
        progress: gr.Progress = gr.Progress(track_tqdm=True),
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

        def report_progress(p: float, desc: str) -> None:
            if progress:
                try:
                    progress(p, desc=desc)
                except Exception:
                    pass

        report_progress(0.05, "Starting Phase 2 processing...")

        assets = await self.service.phase_2_process(
            current_state, progress_callback=report_progress
        )

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
        if current_state.project_dir and selected_path:
            filename = Path(selected_path).name
            canonical_path = Path(current_state.project_dir) / "thumbnails" / filename
            if canonical_path.exists():
                selected_path = str(canonical_path.resolve())
            elif getattr(evt, "index", None) is not None:
                idx = evt.index
                if isinstance(idx, (int, float)):
                    indexed_path = (
                        Path(current_state.project_dir)
                        / "thumbnails"
                        / f"thumbnail_{int(idx) + 1}.png"
                    )
                    if indexed_path.exists():
                        selected_path = str(indexed_path.resolve())
        current_state.selected_thumbnail_path = selected_path
        return f"Selected final thumbnail: {selected_path}", current_state

    def on_check_auth_status(self) -> str:
        """Return a human-readable NotebookLM authentication status string."""
        if self.auth_service.is_authenticated():
            return "✅ Authenticated — NotebookLM is connected."
        return "❌ Not authenticated — click 'Login to NotebookLM' to connect."

    async def on_notebooklm_login(self) -> str:
        """Trigger browser-based NotebookLM login and return result status."""
        return await self.auth_service.login()

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
                        summary_char_count = gr.Markdown(
                            "Character count: 0",
                            elem_id="summary_char_count",
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
                            allow_preview=True,
                            columns=3,
                        )
                        confirm_infographic_btn = gr.Button(
                            "Confirm Infographic", variant="primary"
                        )
                        infographic_status_markdown = gr.Markdown()

                    with gr.Accordion("Step 4: Thumbnail Selection", open=True):
                        thumbnails_gallery = gr.Gallery(
                            label="Generated Thumbnails (Select 1 Final)",
                            allow_preview=True,
                            columns=3,
                        )
                        confirm_thumbnail_btn = gr.Button(
                            "Confirm Thumbnail & Create Shorts Thumbnail", variant="primary"
                        )
                        thumbnail_status_markdown = gr.Markdown()

                    with gr.Accordion("Step 5: Final Outputs", open=True):
                        with gr.Row():
                            with gr.Column():
                                final_video_player = gr.Video(label="Final Video (16:9)")
                                final_video_status_markdown = gr.Markdown()
                            with gr.Column():
                                shorts_video_player = gr.Video(
                                    label="Shorts Video Fancy (9:16)"
                                )
                                shorts_video_status_markdown = gr.Markdown()
                            with gr.Column():
                                shorts_thumb_display = gr.Image(
                                    label="Shorts Thumbnail (9:16)"
                                )
                                shorts_thumb_status_markdown = gr.Markdown()

                    # Event bindings
                    phase1_btn.click(
                        fn=self.on_start_notebooklm,
                        inputs=[drive_link_input, themes_input, session_state],
                        outputs=[
                            summary_textbox,
                            hashtags_checkbox,
                            session_state,
                            summary_status_markdown,
                        ],
                    ).then(
                        fn=self.on_generate_infographics,
                        inputs=[session_state],
                        outputs=[
                            infographics_gallery,
                            session_state,
                            infographic_status_markdown,
                        ],
                    )

                    summary_textbox.change(
                        fn=self.on_summary_change,
                        inputs=[summary_textbox, hashtags_checkbox],
                        outputs=[summary_char_count],
                    )

                    hashtags_checkbox.change(
                        fn=self.on_hashtag_change,
                        inputs=[hashtags_checkbox, summary_textbox, session_state],
                        outputs=[hashtags_checkbox, session_state, summary_char_count],
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
                        fn=self.on_click_confirm_infographic,
                        inputs=[session_state],
                        outputs=[
                            confirm_infographic_btn,
                            infographic_status_markdown,
                        ],
                    )
                    confirm_infographic_btn.click(
                        fn=self.on_create_final_video,
                        inputs=[session_state],
                        outputs=[
                            final_video_player,
                            final_video_status_markdown,
                        ],
                    )
                    confirm_infographic_btn.click(
                        fn=self.on_create_short_video,
                        inputs=[session_state],
                        outputs=[
                            shorts_video_player,
                            shorts_video_status_markdown,
                        ],
                    )
                    confirm_infographic_btn.click(
                        fn=self.on_generate_thumbnails,
                        inputs=[session_state],
                        outputs=[
                            thumbnails_gallery,
                            thumbnail_status_markdown,
                        ],
                    )

                    thumbnails_gallery.select(
                        fn=self.on_select_thumbnail,
                        inputs=[session_state],
                        outputs=[thumbnail_status_markdown, session_state],
                    )

                    confirm_thumbnail_btn.click(
                        fn=self.on_confirm_thumbnail,
                        inputs=[session_state],
                        outputs=[
                            shorts_thumb_display,
                            confirm_thumbnail_btn,
                            shorts_thumb_status_markdown,
                        ],
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

                    gr.Markdown("---")
                    gr.Markdown("### NotebookLM Authentication")
                    gr.Markdown(
                        "Login once with your Google account. "
                        "Credentials are saved locally and reused across sessions."
                    )
                    auth_status_markdown = gr.Markdown(
                        value=self.on_check_auth_status()
                    )
                    notebooklm_login_btn = gr.Button(
                        "Login to NotebookLM",
                        variant="primary",
                        elem_id="notebooklm_login_btn",
                    )
                    notebooklm_login_btn.click(
                        fn=self.on_notebooklm_login,
                        inputs=[],
                        outputs=[auth_status_markdown],
                    )

        return demo
