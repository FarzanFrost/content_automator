"""Tests for class-based Gradio UI and event handlers."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import gradio as gr
import pytest

from app.backend.entities.project import ProjectState
from app.backend.repositories.file_repo import FileRepo
from app.backend.services.automation_service import AutomationService
from app.ui.app import ContentAutomatorUI


def test_ui_init_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify ContentAutomatorUI instantiates default service and repo if not provided."""
    monkeypatch.setenv("GEMINI_IMAGE_API_KEY", "mock-test-key")
    monkeypatch.setenv("GEMINI_CONCEPTS_API_KEY", "mock-test-key")
    ui = ContentAutomatorUI()
    assert isinstance(ui.service, AutomationService)
    assert isinstance(ui.file_repo, FileRepo)


def test_ui_init_dependency_injection() -> None:
    """Verify ContentAutomatorUI accepts injected service and repository dependencies."""
    mock_service = MagicMock(spec=AutomationService)
    mock_file_repo = MagicMock(spec=FileRepo)

    ui = ContentAutomatorUI(service=mock_service, file_repo=mock_file_repo)
    assert ui.service is mock_service
    assert ui.file_repo is mock_file_repo


def test_build_ui_returns_blocks() -> None:
    """Verify build_ui constructs valid gr.Blocks with summary_char_count component."""
    ui = ContentAutomatorUI()
    blocks = ui.build_ui()
    assert isinstance(blocks, gr.Blocks)
    elem_ids = [c.elem_id for c in blocks.blocks.values() if hasattr(c, "elem_id")]
    assert "summary_char_count" in elem_ids


def test_on_hashtag_change_under_max() -> None:
    """Verify selecting 2 or fewer hashtags preserves user selection in state."""
    ui = ContentAutomatorUI()
    state = ProjectState()

    update, updated_state = ui.on_hashtag_change(["#one", "#two"], state)

    assert updated_state.selected_hashtags == ["#one", "#two"]
    assert update["value"] == ["#one", "#two"]


def test_on_hashtag_change_exceeds_max() -> None:
    """Verify selecting more than 2 hashtags restricts selection to max of 2."""
    ui = ContentAutomatorUI()
    state = ProjectState()

    update, updated_state = ui.on_hashtag_change(["#one", "#two", "#three"], state)

    assert updated_state.selected_hashtags == ["#one", "#two"]
    assert update["value"] == ["#one", "#two"]


@pytest.mark.anyio
async def test_on_start_phase_1() -> None:
    """Verify Phase 1 event handler parses inputs, delegates to service, and returns gallery."""
    mock_service = MagicMock(spec=AutomationService)
    return_state = ProjectState(
        project_dir="/workspace/output/khutbah",
        audio_path="/workspace/output/khutbah/audio.mp3",
        summary_v1="AI Generated Summary",
        themes=["peace", "charity"],
        selected_hashtags=["#Peace", "#Charity", "#Khutbah"],
    )
    mock_service.phase_1_process = AsyncMock(
        return_value=(
            return_state,
            ["/workspace/output/khutbah/infographics/infographic_1.png"],
        )
    )

    mock_auth = MagicMock()
    mock_auth.is_authenticated.return_value = True
    ui = ContentAutomatorUI(service=mock_service, auth_service=mock_auth)
    state = ProjectState()

    summary_out, hashtag_out, gallery_out, out_state, status_out = (
        await ui.on_start_phase_1(
            drive_link="https://drive.google.com/file/d/test12345/view",
            themes_str="peace, charity",
            state=state,
        )
    )

    mock_service.phase_1_process.assert_awaited_once_with(
        "https://drive.google.com/file/d/test12345/view",
        ["peace", "charity"],
        n_infographics=3,
    )
    assert summary_out == "AI Generated Summary"
    assert out_state.project_dir == "/workspace/output/khutbah"
    assert hashtag_out["choices"] == ["#Peace", "#Charity", "#Khutbah"]
    assert hashtag_out["value"] == ["#Peace", "#Charity"]
    assert gallery_out == ["/workspace/output/khutbah/infographics/infographic_1.png"]
    assert "Complete" in status_out


def test_on_save_edited_summary_success() -> None:
    """Verify saving edited summary delegates to file_repo with v2_edited.md."""
    mock_file_repo = MagicMock(spec=FileRepo)
    mock_file_repo.save_text_version.return_value = (
        "/workspace/output/khutbah/v2_edited.md"
    )

    ui = ContentAutomatorUI(file_repo=mock_file_repo)
    state = ProjectState(project_dir="/workspace/output/khutbah")

    status, out_state = ui.on_save_edited_summary("Revised Khutbah Summary", state)

    mock_file_repo.save_text_version.assert_called_once_with(
        "Revised Khutbah Summary", "v2_edited.md", "/workspace/output/khutbah"
    )
    assert "/workspace/output/khutbah/v2_edited.md" in status
    assert out_state is state


def test_on_save_edited_summary_missing_project_dir() -> None:
    """Verify saving edited summary without active project directory returns error."""
    mock_file_repo = MagicMock(spec=FileRepo)
    ui = ContentAutomatorUI(file_repo=mock_file_repo)
    state = ProjectState(project_dir="")

    status, out_state = ui.on_save_edited_summary("Edited summary", state)

    assert "Error" in status
    mock_file_repo.save_text_version.assert_not_called()


def test_on_select_infographic_dict_event() -> None:
    """Verify on_select_infographic extracts path and updates state from dict event."""
    ui = ContentAutomatorUI()
    state = ProjectState()
    mock_event = MagicMock(spec=gr.SelectData)
    mock_event.value = {
        "image": {"path": "/workspace/output/khutbah/infographics/infographic_2.png"}
    }

    msg, out_state = ui.on_select_infographic(mock_event, state)

    assert out_state.selected_infographic_path == (
        "/workspace/output/khutbah/infographics/infographic_2.png"
    )
    assert "infographic_2.png" in msg


def test_on_select_infographic_str_event() -> None:
    """Verify on_select_infographic extracts path and updates state from string event."""
    ui = ContentAutomatorUI()
    state = ProjectState()
    mock_event = MagicMock(spec=gr.SelectData)
    mock_event.value = "/workspace/output/khutbah/infographics/infographic_1.png"

    msg, out_state = ui.on_select_infographic(mock_event, state)

    assert out_state.selected_infographic_path == (
        "/workspace/output/khutbah/infographics/infographic_1.png"
    )
    assert "infographic_1.png" in msg


@pytest.mark.anyio
async def test_on_confirm_infographic_missing_selection() -> None:
    """Verify on_confirm_infographic rejects execution if no infographic selected."""
    ui = ContentAutomatorUI()
    state = ProjectState(selected_infographic_path="")

    gallery_out, final_vid, shorts_vid, thumb, status_msg, out_state = (
        await ui.on_confirm_infographic(state)
    )

    assert "Error" in status_msg
    assert gallery_out == []
    assert final_vid is None
    assert shorts_vid is None
    assert thumb is None


@pytest.mark.anyio
async def test_on_confirm_infographic_success() -> None:
    """Verify on_confirm_infographic invokes Phase 2 and populates Step 4 and 5 outputs."""
    mock_service = MagicMock(spec=AutomationService)
    mock_service.phase_2_process = AsyncMock(
        return_value=[
            "/workspace/output/khutbah/thumbnails/thumbnail_1.png",
            "/workspace/output/khutbah/thumbnails/thumbnail_2.png",
            "/workspace/output/khutbah/final_video.mp4",
            "/workspace/output/khutbah/shorts_video_fancy.mp4",
            "/workspace/output/khutbah/shorts_thumbnail.png",
        ]
    )

    ui = ContentAutomatorUI(service=mock_service)
    state = ProjectState(
        project_dir="/workspace/output/khutbah",
        selected_infographic_path="/workspace/output/khutbah/infographics/infographic_1.png",
    )

    gallery_out, final_vid, shorts_vid, thumb, status_msg, out_state = (
        await ui.on_confirm_infographic(state)
    )

    mock_service.phase_2_process.assert_awaited_once()
    assert mock_service.phase_2_process.call_args[0][0] == state
    assert "progress_callback" in mock_service.phase_2_process.call_args[1]
    assert gallery_out == [
        "/workspace/output/khutbah/thumbnails/thumbnail_1.png",
        "/workspace/output/khutbah/thumbnails/thumbnail_2.png",
    ]
    assert final_vid == "/workspace/output/khutbah/final_video.mp4"
    assert shorts_vid == "/workspace/output/khutbah/shorts_video_fancy.mp4"
    assert thumb == "/workspace/output/khutbah/shorts_thumbnail.png"
    assert "YouTube" in status_msg


def test_on_select_thumbnail() -> None:
    """Verify on_select_thumbnail extracts path and updates state."""
    ui = ContentAutomatorUI()
    state = ProjectState()
    mock_event = MagicMock(spec=gr.SelectData)
    mock_event.value = {
        "image": {"path": "/workspace/output/khutbah/thumbnails/thumbnail_3.png"}
    }

    msg, out_state = ui.on_select_thumbnail(mock_event, state)

    assert out_state.selected_thumbnail_path == (
        "/workspace/output/khutbah/thumbnails/thumbnail_3.png"
    )
    assert "thumbnail_3.png" in msg


def test_on_select_infographic_resolves_temp_path_to_project_file(tmp_path: Path) -> None:
    """Verify on_select_infographic maps Gradio temp cache path to canonical project path."""
    project_dir = tmp_path / "project"
    infographics_dir = project_dir / "infographics"
    infographics_dir.mkdir(parents=True)
    real_file = infographics_dir / "infographic_1.png"
    real_file.write_bytes(b"canonical image")

    ui = ContentAutomatorUI()
    state = ProjectState(project_dir=str(project_dir))
    mock_event = MagicMock(spec=gr.SelectData)
    mock_event.value = {
        "image": {"path": "/tmp/gradio/cache/infographic_1.png"}
    }
    mock_event.index = 0

    msg, out_state = ui.on_select_infographic(mock_event, state)

    assert out_state.selected_infographic_path == str(real_file.resolve())
    assert "infographic_1.png" in msg


def test_on_select_thumbnail_resolves_temp_path_to_project_file(tmp_path: Path) -> None:
    """Verify on_select_thumbnail maps Gradio temp cache path to canonical project path."""
    project_dir = tmp_path / "project"
    thumbnails_dir = project_dir / "thumbnails"
    thumbnails_dir.mkdir(parents=True)
    real_file = thumbnails_dir / "thumbnail_2.png"
    real_file.write_bytes(b"canonical thumbnail")

    ui = ContentAutomatorUI()
    state = ProjectState(project_dir=str(project_dir))
    mock_event = MagicMock(spec=gr.SelectData)
    mock_event.value = {
        "image": {"path": "/tmp/gradio/cache/thumbnail_2.png"}
    }
    mock_event.index = 1

    msg, out_state = ui.on_select_thumbnail(mock_event, state)

    assert out_state.selected_thumbnail_path == str(real_file.resolve())
    assert "thumbnail_2.png" in msg


@pytest.mark.anyio
async def test_on_start_phase_1_awaits_background_tasks() -> None:
    """Verify on_start_phase_1 awaits any background tasks before returning."""
    mock_service = MagicMock(spec=AutomationService)
    task_completed = False

    async def sample_bg_task():
        nonlocal task_completed
        await asyncio.sleep(0.01)
        task_completed = True

    task = asyncio.create_task(sample_bg_task())
    mock_service._background_tasks = {task}

    return_state = ProjectState(
        project_dir="/workspace/output/khutbah",
        audio_path="/workspace/output/khutbah/audio.mp3",
        summary_v1="Summary",
        themes=[],
        selected_hashtags=[],
    )
    mock_service.phase_1_process = AsyncMock(
        return_value=(return_state, ["/workspace/output/khutbah/infographics/infographic_1.png"])
    )
    mock_auth = MagicMock()
    mock_auth.is_authenticated.return_value = True

    ui = ContentAutomatorUI(service=mock_service, auth_service=mock_auth)
    state = ProjectState()

    await ui.on_start_phase_1("https://drive.google.com/test", "", state)
    assert task_completed is True


def test_on_check_auth_status_authenticated() -> None:
    """Verify on_check_auth_status returns authenticated message when logged in."""
    mock_auth = MagicMock()
    mock_auth.is_authenticated.return_value = True

    ui = ContentAutomatorUI(auth_service=mock_auth)
    result = ui.on_check_auth_status()

    assert "Authenticated" in result
    mock_auth.is_authenticated.assert_called_once()


def test_on_check_auth_status_not_authenticated() -> None:
    """Verify on_check_auth_status returns not-authenticated message when no session."""
    mock_auth = MagicMock()
    mock_auth.is_authenticated.return_value = False

    ui = ContentAutomatorUI(auth_service=mock_auth)
    result = ui.on_check_auth_status()

    assert "Not authenticated" in result
    mock_auth.is_authenticated.assert_called_once()


@pytest.mark.anyio
async def test_on_notebooklm_login_delegates_to_auth_service() -> None:
    """Verify on_notebooklm_login awaits auth_service.login and returns result."""
    mock_auth = MagicMock()
    mock_auth.login = AsyncMock(return_value="Authenticated. NotebookLM login successful.")

    ui = ContentAutomatorUI(auth_service=mock_auth)
    result = await ui.on_notebooklm_login()

    assert result == "Authenticated. NotebookLM login successful."
    mock_auth.login.assert_awaited_once()


@pytest.mark.anyio
async def test_on_start_phase_1_unauthenticated_returns_error() -> None:
    """Verify on_start_phase_1 returns error message when NotebookLM is not authenticated."""
    mock_auth = MagicMock()
    mock_auth.is_authenticated.return_value = False
    mock_service = AsyncMock()

    ui = ContentAutomatorUI(service=mock_service, auth_service=mock_auth)
    summary, hashtags_update, placeholders, new_state, status_msg = (
        await ui.on_start_phase_1("https://drive.google.com/test", "Theme1")
    )

    assert "not authenticated" in status_msg.lower()
    mock_service.phase_1_process.assert_not_called()


def test_on_summary_change() -> None:
    """Verify on_summary_change returns formatted character count string."""
    ui = ContentAutomatorUI()

    assert ui.on_summary_change("Hello world") == "Character count: 11"
    assert ui.on_summary_change("") == "Character count: 0"
    assert ui.on_summary_change(None) == "Character count: 0"


@pytest.mark.anyio
async def test_on_start_notebooklm_success() -> None:
    """Verify on_start_notebooklm executes NotebookLM step and returns summary and hashtags."""
    mock_service = MagicMock(spec=AutomationService)
    state = ProjectState(
        project_dir="/workspace/proj",
        summary_v1="NotebookLM Summary",
        selected_hashtags=["#A", "#B", "#C"],
    )
    mock_service.generate_notebooklm_artifacts = AsyncMock(return_value=state)
    mock_auth = MagicMock()
    mock_auth.is_authenticated.return_value = True

    ui = ContentAutomatorUI(service=mock_service, auth_service=mock_auth)
    summary, hashtags_update, out_state, status_msg = await ui.on_start_notebooklm(
        "https://drive.google.com/test", "faith, hope"
    )

    mock_service.generate_notebooklm_artifacts.assert_awaited_once_with(
        "https://drive.google.com/test", ["faith", "hope"]
    )
    assert summary == "NotebookLM Summary"
    assert hashtags_update["choices"] == ["#A", "#B", "#C"]
    assert hashtags_update["value"] == ["#A", "#B"]
    assert "Complete" in status_msg


@pytest.mark.anyio
async def test_on_generate_infographics_success() -> None:
    """Verify on_generate_infographics invokes service and returns infographic paths."""
    mock_service = MagicMock(spec=AutomationService)
    mock_service.generate_infographics = AsyncMock(
        return_value=["/workspace/proj/infographics/infographic_1.png"]
    )
    ui = ContentAutomatorUI(service=mock_service)
    state = ProjectState(project_dir="/workspace/proj", summary_v1="Summary")

    paths, out_state, status_msg = await ui.on_generate_infographics(state)

    mock_service.generate_infographics.assert_awaited_once_with(state, n_infographics=3)
    assert paths == ["/workspace/proj/infographics/infographic_1.png"]
    assert "Complete" in status_msg


def test_on_click_confirm_infographic() -> None:
    """Verify on_click_confirm_infographic disables button if infographic selected."""
    ui = ContentAutomatorUI()
    state_valid = ProjectState(selected_infographic_path="/path/to/info.png")
    btn_update, msg = ui.on_click_confirm_infographic(state_valid)
    assert btn_update["interactive"] is False
    assert "confirmed" in msg.lower()

    state_invalid = ProjectState(selected_infographic_path="")
    btn_update_inv, msg_inv = ui.on_click_confirm_infographic(state_invalid)
    assert btn_update_inv["interactive"] is True
    assert "Error" in msg_inv


@pytest.mark.anyio
async def test_on_create_final_video() -> None:
    """Verify on_create_final_video invokes service.create_final_video."""
    mock_service = MagicMock(spec=AutomationService)
    mock_service.create_final_video = AsyncMock(return_value="/workspace/final.mp4")
    ui = ContentAutomatorUI(service=mock_service)
    state = ProjectState(selected_infographic_path="/path/to/info.png")

    path, status = await ui.on_create_final_video(state)
    assert path == "/workspace/final.mp4"
    assert "Final video rendered" in status


@pytest.mark.anyio
async def test_on_create_short_video() -> None:
    """Verify on_create_short_video invokes service.create_short_video."""
    mock_service = MagicMock(spec=AutomationService)
    mock_service.create_short_video = AsyncMock(return_value="/workspace/short.mp4")
    ui = ContentAutomatorUI(service=mock_service)
    state = ProjectState(selected_infographic_path="/path/to/info.png")

    path, status = await ui.on_create_short_video(state)
    assert path == "/workspace/short.mp4"
    assert "Shorts video rendered" in status


@pytest.mark.anyio
async def test_on_generate_thumbnails() -> None:
    """Verify on_generate_thumbnails invokes service.generate_thumbnails."""
    mock_service = MagicMock(spec=AutomationService)
    mock_service.generate_thumbnails = AsyncMock(
        return_value=["/workspace/thumb_1.png", "/workspace/thumb_2.png"]
    )
    ui = ContentAutomatorUI(service=mock_service)
    state = ProjectState(selected_infographic_path="/path/to/info.png")

    paths, status = await ui.on_generate_thumbnails(state)
    assert len(paths) == 2
    assert "Thumbnails generated" in status


@pytest.mark.anyio
async def test_on_confirm_thumbnail() -> None:
    """Verify on_confirm_thumbnail invokes service.create_short_thumbnail on selected thumbnail."""
    mock_service = MagicMock(spec=AutomationService)
    mock_service.create_short_thumbnail = AsyncMock(
        return_value="/workspace/shorts_thumbnail.png"
    )
    ui = ContentAutomatorUI(service=mock_service)
    state = ProjectState(selected_thumbnail_path="/workspace/thumb_1.png")

    path, btn_update, status = await ui.on_confirm_thumbnail(state)
    assert path == "/workspace/shorts_thumbnail.png"
    assert btn_update["interactive"] is False
    assert "created" in status.lower()

    # Without selection returns error and leaves button enabled
    state_empty = ProjectState(selected_thumbnail_path="")
    path_err, btn_update_err, status_err = await ui.on_confirm_thumbnail(state_empty)
    assert path_err is None
    assert btn_update_err["interactive"] is True
    assert "Error" in status_err


