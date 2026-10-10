"""Application launch entry point for Content Automator."""

import os
from pathlib import Path

from app.backend.config.settings import AppSettings
from app.backend.services.automation_service import AutomationService
from app.ui.app import ContentAutomatorUI


def main() -> None:
    """Initialize services and launch the Gradio user interface."""
    service = AutomationService()
    ui = ContentAutomatorUI(service=service)
    demo = ui.build_ui()
    base_output_dir = str(
        Path(AppSettings.load().BASE_OUTPUT_DIR or "output").resolve()
    )
    demo.launch(
        server_name=os.getenv("SERVER_NAME", "127.0.0.1"),
        server_port=int(os.getenv("SERVER_PORT", "7860")),
        share=False,
        allowed_paths=[base_output_dir],
    )


if __name__ == "__main__":
    main()
