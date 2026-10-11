"""NotebookLM repository wrapping notebooklm-py for content intelligence."""

import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, List, Optional

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

    @asynccontextmanager
    async def _get_client(self) -> AsyncIterator[Any]:
        """Provide NotebookLM client context from injected client, auth, or storage."""
        if self._client is not None:
            yield self._client
            return

        os.environ.setdefault("NOTEBOOKLM_HEADLESS_REAUTH", "1")

        if self._auth is not None:
            async with NotebookLMClient(auth=self._auth, keepalive=600) as client:
                yield client
        else:
            async with NotebookLMClient.from_storage(
                keepalive=600,
                allow_headless=True,
            ) as client:
                yield client

    async def generate_summary(self, audio_path: str) -> str:
        """Generate comprehensive summary from uploaded audio resource."""
        async with self._get_client() as client:
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
        async with self._get_client() as client:
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
