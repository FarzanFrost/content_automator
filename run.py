"""Application launch entry point for Content Automator."""

import os

from app.backend.services.automation_service import AutomationService
from app.ui.app import ContentAutomatorUI


def main() -> None:
    """Initialize services and launch the Gradio user interface."""
    service = AutomationService()
    ui = ContentAutomatorUI(service=service)
    demo = ui.build_ui()
    demo.launch(
        server_name=os.getenv("SERVER_NAME", "127.0.0.1"),
        server_port=int(os.getenv("SERVER_PORT", "7860")),
        share=False,
    )


if __name__ == "__main__":
    main()
