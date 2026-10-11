"""Tests for NotebookLMAuthService."""

import asyncio
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from app.backend.services.notebooklm_auth_service import NotebookLMAuthService


class TestNotebookLMAuthServiceIsAuthenticated(unittest.TestCase):
    def test_returns_false_when_storage_file_missing(self) -> None:
        """is_authenticated returns False when storage_state.json does not exist."""
        service = NotebookLMAuthService(
            storage_path=Path("/nonexistent/path/storage_state.json")
        )
        self.assertFalse(service.is_authenticated())

    def test_returns_false_when_storage_file_invalid_json(self) -> None:
        """is_authenticated returns False when storage_state.json contains invalid JSON."""
        with TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir) / "storage_state.json"
            storage.write_text("invalid json content", encoding="utf-8")
            service = NotebookLMAuthService(storage_path=storage)
            self.assertFalse(service.is_authenticated())

    def test_returns_false_when_missing_required_cookies(self) -> None:
        """is_authenticated returns False when required cookies (SID, __Secure-1PSIDTS) are missing."""
        with TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir) / "storage_state.json"
            incomplete_state = {
                "cookies": [
                    {"name": "__Host-GAPS", "value": "123"},
                    {"name": "NID", "value": "456"},
                ]
            }
            storage.write_text(json.dumps(incomplete_state), encoding="utf-8")
            service = NotebookLMAuthService(storage_path=storage)
            self.assertFalse(service.is_authenticated())

    def test_returns_true_when_required_cookies_present(self) -> None:
        """is_authenticated returns True when storage_state.json contains SID and __Secure-1PSIDTS."""
        with TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir) / "storage_state.json"
            valid_state = {
                "cookies": [
                    {"name": "SID", "value": "sid_val"},
                    {"name": "__Secure-1PSIDTS", "value": "psidts_val"},
                    {"name": "NID", "value": "nid_val"},
                ]
            }
            storage.write_text(json.dumps(valid_state), encoding="utf-8")
            service = NotebookLMAuthService(storage_path=storage)
            self.assertTrue(service.is_authenticated())


class TestNotebookLMAuthServiceInvalidate(unittest.TestCase):
    def test_invalidate_auth_removes_storage_and_lock_files(self) -> None:
        """invalidate_auth removes storage_state.json and associated .lock file."""
        with TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir) / "storage_state.json"
            lock_file = Path(tmpdir) / ".storage_state.json.lock"
            storage.write_text("{}", encoding="utf-8")
            lock_file.write_text("lock", encoding="utf-8")

            service = NotebookLMAuthService(storage_path=storage)
            service.invalidate_auth()

            self.assertFalse(storage.exists())
            self.assertFalse(lock_file.exists())


class TestNotebookLMAuthServiceLogin(unittest.IsolatedAsyncioTestCase):
    async def test_login_invalidates_existing_and_returns_success_when_authenticated(
        self,
    ) -> None:
        """login() invalidates existing storage and returns success when new valid cookies written."""
        with TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir) / "storage_state.json"
            # Existing invalid/stale state
            storage.write_text(json.dumps({"cookies": []}), encoding="utf-8")
            service = NotebookLMAuthService(storage_path=storage)

            def fake_run() -> None:
                valid_state = {
                    "cookies": [
                        {"name": "SID", "value": "new_sid"},
                        {"name": "__Secure-1PSIDTS", "value": "new_psidts"},
                    ]
                }
                storage.write_text(json.dumps(valid_state), encoding="utf-8")

            with patch.object(service, "_run_browser_login", side_effect=fake_run):
                result = await service.login()

        self.assertIn("successful", result)

    async def test_login_returns_missing_cookies_message_when_no_valid_cookies_written(
        self,
    ) -> None:
        """login() returns fallback message if storage lacks required cookies after login attempt."""
        with TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir) / "storage_state.json"
            service = NotebookLMAuthService(storage_path=storage)

            def fake_run_empty() -> None:
                # Writes incomplete cookies like in the real failure
                storage.write_text(
                    json.dumps({"cookies": [{"name": "NID", "value": "1"}]}),
                    encoding="utf-8",
                )

            with patch.object(
                service, "_run_browser_login", side_effect=fake_run_empty
            ):
                result = await service.login()

        self.assertIn("required cookies not found", result)

    async def test_login_returns_playwright_not_installed_on_import_error(self) -> None:
        """login() returns install instructions when Playwright is missing."""
        with TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir) / "storage_state.json"
            service = NotebookLMAuthService(storage_path=storage)

            with patch.object(
                service, "_run_browser_login", side_effect=ImportError("playwright")
            ):
                result = await service.login()

        self.assertIn("Playwright not installed", result)

    async def test_login_returns_error_message_on_exception(self) -> None:
        """login() returns error message when _run_browser_login raises unexpected exception."""
        with TemporaryDirectory() as tmpdir:
            storage = Path(tmpdir) / "storage_state.json"
            service = NotebookLMAuthService(storage_path=storage)

            with patch.object(
                service, "_run_browser_login", side_effect=RuntimeError("network error")
            ):
                result = await service.login()

        self.assertIn("Login failed", result)
        self.assertIn("network error", result)


class TestNotebookLMAuthServiceBrowserSelection(unittest.TestCase):
    def test_get_preferred_browser_returns_chrome_when_available(self) -> None:
        """_get_preferred_browser returns 'chrome' when Google Chrome is available."""
        service = NotebookLMAuthService()
        with patch(
            "shutil.which",
            return_value="C:/Program Files/Google/Chrome/Application/chrome.exe",
        ), patch("notebooklm.auth.ensure_browser_login_available", return_value=None):
            browser = service._get_preferred_browser()
            self.assertEqual(browser, "chrome")

    def test_get_preferred_browser_falls_back_to_chromium_when_chrome_missing(
        self,
    ) -> None:
        """_get_preferred_browser falls back to 'chromium' when Chrome is not available."""
        service = NotebookLMAuthService()
        with patch("shutil.which", return_value=None), patch(
            "pathlib.Path.exists", return_value=False
        ):
            browser = service._get_preferred_browser()
            self.assertEqual(browser, "chromium")


class TestNotebookLMAuthServiceRunBrowserLogin(unittest.TestCase):
    def test_run_browser_login_uses_fresh_false_and_preferred_browser(self) -> None:
        """_run_browser_login prepares paths with fresh=False to preserve persistent session."""
        service = NotebookLMAuthService()
        mock_outcome = MagicMock()
        mock_outcome.browser_profile = Path("/tmp/browser_profile")
        mock_outcome.storage_path = Path("/tmp/storage_state.json")

        with patch(
            "notebooklm._app.login_browser.prepare_login_paths",
            return_value=mock_outcome,
        ) as mock_prepare, patch.object(
            service, "_get_preferred_browser", return_value="chrome"
        ), patch(
            "notebooklm.cli.playwright_login_io.run_login"
        ) as mock_run_login:
            service._run_browser_login()

            mock_prepare.assert_called_once_with(
                profile=None, storage=None, fresh=False
            )
            mock_run_login.assert_called_once()
            plan = mock_run_login.call_args[0][0]
            self.assertEqual(plan.browser, "chrome")
            self.assertEqual(plan.browser_profile, mock_outcome.browser_profile)

    def test_run_browser_login_raises_runtime_error_on_login_path_error(self) -> None:
        """_run_browser_login raises RuntimeError when prepare_login_paths returns LoginPathError."""
        from notebooklm._app.login_browser import LoginPathError

        service = NotebookLMAuthService()
        error_outcome = LoginPathError(
            code="UNOWNED_BROWSER_PROFILE", browser_profile=Path("/tmp/err")
        )

        with patch(
            "notebooklm._app.login_browser.prepare_login_paths",
            return_value=error_outcome,
        ):
            with self.assertRaises(RuntimeError):
                service._run_browser_login()
