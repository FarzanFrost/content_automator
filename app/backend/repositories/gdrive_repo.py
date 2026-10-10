"""Google Drive repository handling audio downloads and filename resolution."""

import re
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

import httpx


class GoogleDriveRepo:
    """Repository managing audio resource downloads from Google Drive."""

    def __init__(self, http_client: Optional[httpx.Client] = None) -> None:
        """Initialize GoogleDriveRepo with optional HTTP client injection."""
        self._client = http_client or httpx.Client(follow_redirects=True, timeout=60.0)

    def extract_file_id(self, url: str) -> Optional[str]:
        """Extract Google Drive file ID from standard sharing or direct links."""
        # Check standard path /file/d/{id}
        path_match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
        if path_match:
            return path_match.group(1)

        # Check query parameters like ?id={id}
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        if "id" in query_params and query_params["id"]:
            return query_params["id"][0]

        return None

    def extract_filename_from_header(
        self, content_disposition: Optional[str], default_id: str = "audio_download"
    ) -> str:
        """Extract filename from Content-Disposition header with fallback."""
        if content_disposition:
            # Match filename="example.mp3" or filename=example.mp3
            match = re.search(
                r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\n]+)["\']?',
                content_disposition,
            )
            if match:
                return match.group(1).strip()

        return f"{default_id}.mp3"

    def download_audio(self, url: str, dest_dir: str) -> str:
        """Download audio file from Google Drive URL to target directory."""
        target_dir = Path(dest_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        file_id = self.extract_file_id(url)
        direct_url = (
            f"https://drive.google.com/uc?export=download&id={file_id}"
            if file_id
            else url
        )

        response = self._client.get(direct_url)
        response.raise_for_status()

        content_disp = response.headers.get("Content-Disposition")
        filename = self.extract_filename_from_header(
            content_disp, default_id=file_id or "downloaded_audio"
        )
        file_path = target_dir / filename

        temp_path = target_dir / f".tmp_{filename}"
        with open(temp_path, "wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)

        temp_path.replace(file_path)
        return str(file_path.resolve())
