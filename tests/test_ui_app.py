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
    """Verify Phase 1 event handler parses inputs and delegates to service."""
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

    summary_out, hashtag_out, out_state, status_out = await ui.on_start_phase_1(
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
