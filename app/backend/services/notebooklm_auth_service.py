"""NotebookLM authentication service wrapping notebooklm-py browser login."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_STORAGE_PATH = (
    Path.home() / ".notebooklm" / "profiles" / "default" / "storage_state.json"
)
_REQUIRED_COOKIES = frozenset({"SID", "__Secure-1PSIDTS"})


class NotebookLMAuthService:
    """Service that checks auth status and triggers browser-based NotebookLM login."""

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize with optional override for the storage_state.json path."""
        self._storage_path = storage_path or _DEFAULT_STORAGE_PATH

    def is_authenticated(self) -> bool:
        """Return True if storage_state.json exists and contains required Google session cookies."""
        if not self._storage_path.exists():
            return False
        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            cookies = state.get("cookies", [])
            if not isinstance(cookies, list):
                return False
            cookie_names = {c.get("name") for c in cookies if isinstance(c, dict)}
            return _REQUIRED_COOKIES.issubset(cookie_names)
        except Exception:
            return False

    def invalidate_auth(self) -> None:
        """Invalidate existing authentication by deleting storage_state.json and lock files."""
        if self._storage_path.exists():
            try:
                self._storage_path.unlink()
            except OSError as exc:
                logger.warning(
                    "Could not delete storage file %s: %s", self._storage_path, exc
                )
        lock_file = self._storage_path.parent / f".{self._storage_path.name}.lock"
        if lock_file.exists():
            try:
                lock_file.unlink()
            except OSError as exc:
                logger.warning("Could not delete lock file %s: %s", lock_file, exc)

    async def login(self) -> str:
        """Invalidate existing auth, launch browser login, and return status message.

        Runs the Playwright-based `notebooklm login` flow in a background
        thread so the Gradio event loop is not blocked. Returns when
        authentication is complete and storage_state.json is written.
        """
        self.invalidate_auth()
        try:
            await asyncio.to_thread(self._run_browser_login)
            if self.is_authenticated():
                return "✅ Authenticated. NotebookLM login successful."
            return "❌ Login completed but required cookies not found. Please re-try login."
        except ImportError:
            return (
                "Playwright not installed. Run:\n"
                '  pip install "notebooklm-py[browser]"\n'
                "  playwright install chromium"
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("NotebookLM browser login failed")
            return f"❌ Login failed: {exc}"

    def _get_preferred_browser(self) -> str:
        """Return 'chrome' if system Google Chrome is available, else 'chromium'."""
        chrome_exe = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
        if shutil.which("chrome") or chrome_exe.exists():
            try:
                from notebooklm import auth

                auth.ensure_browser_login_available(
                    "chrome",
                    emit=lambda *_: None,
                    fail=lambda code: (_ for _ in ()).throw(
                        RuntimeError(f"Chrome exit {code}")
                    ),
                )
                return "chrome"
            except Exception:
                pass
        return "chromium"

    def _run_browser_login(self) -> None:
        """Synchronous Playwright login — called from asyncio.to_thread."""
        from notebooklm._app.login_browser import (BrowserLoginPlan,
                                                   LoginPathError,
                                                   prepare_login_paths)
        from notebooklm._env import get_base_url
        from notebooklm.cli.playwright_login_io import run_login
        from playwright.sync_api import Page

        storage_arg = (
            str(self._storage_path)
            if self._storage_path != _DEFAULT_STORAGE_PATH
            else None
        )
        outcome = prepare_login_paths(profile=None, storage=storage_arg, fresh=False)
        if isinstance(outcome, LoginPathError):
            raise RuntimeError(f"Login path error: {outcome}")

        browser_choice = self._get_preferred_browser()

        plan = BrowserLoginPlan(
            browser=browser_choice,
            browser_profile=outcome.browser_profile,
            storage_path=outcome.storage_path,
            include_domains=None,
            login_timeout_s=300,
        )

        base_url = get_base_url().rstrip("/")
        login_url = f"{base_url}/login"
        target_roots = {
            f"{base_url}/",
            f"{base_url}",
            "https://notebook.google.com/",
            "https://notebook.google.com",
            "https://notebooklm.google.com/",
            "https://notebooklm.google.com",
        }

        original_goto = Page.goto
        navigated_to_login = False

        def patched_goto(page_self: Page, url: str, *args: Any, **kwargs: Any) -> Any:
            nonlocal navigated_to_login
            if not navigated_to_login and url in target_roots:
                navigated_to_login = True
                return original_goto(page_self, login_url, *args, **kwargs)
            return original_goto(page_self, url, *args, **kwargs)

        Page.goto = patched_goto
        try:
            run_login(plan)
        finally:
            Page.goto = original_goto
