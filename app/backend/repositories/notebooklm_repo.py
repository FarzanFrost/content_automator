"""NotebookLM repository wrapping notebooklm-py for content intelligence."""

import re
from pathlib import Path
from typing import Any, List, Optional

try:
    from notebooklm import NotebookLMClient
except ImportError:
    NotebookLMClient = Any  # type: ignore[assignment, misc]

from app.backend.utils.prompt_manager import PromptManager


class NotebookLMRepo:
    """Repository wrapping NotebookLM API to extract audio summaries and hashtags."""

    def __init__(
        self,
        client: Optional[Any] = None,
        auth: Optional[Any] = None,
        prompt_manager: Optional[PromptManager] = None,
    ) -> None:
        """Initialize NotebookLM repository with optional client, auth tokens, or prompt manager."""
        self._client = client
        self._auth = auth
        self._prompt_manager = prompt_manager or PromptManager()

    def _get_client(self) -> Any:
        """Get existing client or create instance from auth/storage."""
        if self._client is not None:
            return self._client

        if self._auth is not None:
            self._client = NotebookLMClient(auth=self._auth)
        else:
            self._client = NotebookLMClient.from_storage()

        return self._client

    async def generate_summary(self, audio_path: str) -> str:
        """Generate comprehensive summary from uploaded audio resource."""
        client = self._get_client()
        title = f"summary_{Path(audio_path).stem}"
        notebook = await client.notebooks.create(title=title)

        await client.sources.add_file(
            notebook_id=notebook.id,
            file_path=audio_path,
            wait=True,
        )

        response = await client.chat.ask(
            notebook_id=notebook.id,
            question=self._prompt_manager.get_summary_prompt(),
        )
        return response.answer

    async def generate_hashtags(self, audio_path: str) -> List[str]:
        """Extract relevant YouTube hashtags from uploaded audio resource."""
        client = self._get_client()
        title = f"hashtags_{Path(audio_path).stem}"
        notebook = await client.notebooks.create(title=title)

        await client.sources.add_file(
            notebook_id=notebook.id,
            file_path=audio_path,
            wait=True,
        )

        response = await client.chat.ask(
            notebook_id=notebook.id,
            question=self._prompt_manager.get_hashtags_prompt(),
        )

        raw_text = response.answer
        found_tags = re.findall(r"#\w+", raw_text)
        if found_tags:
            return found_tags

        # Fallback to comma/whitespace separated words
        tokens = [t.strip().strip(",") for t in raw_text.split()]
        return [f"#{t.lstrip('#')}" for t in tokens if t]
