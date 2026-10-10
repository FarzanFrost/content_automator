"""Tests for class-based Gradio UI and event handlers."""

from unittest.mock import AsyncMock, MagicMock

import gradio as gr
import pytest

from app.backend.entities.project import ProjectState
from app.backend.repositories.file_repo import FileRepo
from app.backend.services.automation_service import AutomationService
from app.ui.app import ContentAutomatorUI


def test_ui_init_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify ContentAutomatorUI instantiates default service and repo if not provided."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock-test-key")
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
    """Verify build_ui constructs and returns a valid gr.Blocks container."""
    ui = ContentAutomatorUI()
    blocks = ui.build_ui()
    assert isinstance(blocks, gr.Blocks)


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

    ui = ContentAutomatorUI(service=mock_service)
    state = ProjectState()

    summary_out, hashtag_out, gallery_out, out_state, status_out = await ui.on_start_phase_1(
        drive_link="https://drive.google.com/file/d/test12345/view",
        themes_str="peace, charity",
        state=state,
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

    mock_service.phase_2_process.assert_awaited_once_with(state)
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

