"""Tests for FFmpegWrapper utility class."""

import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


class TestFFmpegWrapper(unittest.IsolatedAsyncioTestCase):
    """Tests for FFmpegWrapper async video processing methods."""

    # --- create_final_video ---

    @patch("app.backend.utils.ffmpeg_wrapper.asyncio.create_subprocess_exec")
    async def test_create_final_video_runs_ffmpeg(self, mock_exec: AsyncMock) -> None:
        """Verifies ffmpeg subprocess is invoked with correct output path."""
        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        from app.backend.utils.ffmpeg_wrapper import FFmpegWrapper

        wrapper = FFmpegWrapper()
        await wrapper.create_final_video(
            img_path="thumb.jpg",
            audio_path="sermon.mp3",
            out_path="output/final.mp4",
        )

        mock_exec.assert_awaited_once()
        args = mock_exec.call_args[0]
        self.assertIn("output/final.mp4", args)
        self.assertIn("-c:a", args)
        idx = args.index("-c:a")
        self.assertEqual(args[idx + 1], "copy")
        self.assertIn("-vf", args)
        vf_idx = args.index("-vf")
        self.assertEqual(args[vf_idx + 1], "pad=ceil(iw/2)*2:ceil(ih/2)*2")
        self.assertIn("-preset", args)
        preset_idx = args.index("-preset")
        self.assertEqual(args[preset_idx + 1], "veryfast")


    @patch("app.backend.utils.ffmpeg_wrapper.asyncio.create_subprocess_exec")
    async def test_create_final_video_raises_on_nonzero_returncode(
        self, mock_exec: AsyncMock
    ) -> None:
        """Raises RuntimeError when ffmpeg exits with nonzero code."""
        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b"error output"))
        mock_proc.returncode = 1
        mock_exec.return_value = mock_proc

        from app.backend.utils.ffmpeg_wrapper import FFmpegWrapper

        wrapper = FFmpegWrapper()
        with self.assertRaises(RuntimeError):
            await wrapper.create_final_video(
                img_path="thumb.jpg",
                audio_path="sermon.mp3",
                out_path="output/final.mp4",
            )

    # --- create_short_video ---

    @patch("app.backend.utils.ffmpeg_wrapper.asyncio.create_subprocess_exec")
    async def test_create_short_video_runs_ffmpeg(self, mock_exec: AsyncMock) -> None:
        """Verifies ffmpeg subprocess is invoked with correct output path."""
        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        from app.backend.utils.ffmpeg_wrapper import FFmpegWrapper

        wrapper = FFmpegWrapper()
        await wrapper.create_short_video(
            img_path="thumb.jpg",
            bgm_path="bgm.mp3",
            out_path="output/short.mp4",
        )

        mock_exec.assert_awaited_once()
        args = mock_exec.call_args[0]
        self.assertIn("output/short.mp4", args)
        self.assertIn("-vf", args)
        self.assertNotIn("-filter_complex", args)
        self.assertNotIn("-stream_loop", args)
        self.assertNotIn("-t", args)
        self.assertIn("-c:a", args)
        idx = args.index("-c:a")
        self.assertEqual(args[idx + 1], "copy")
        self.assertIn("-shortest", args)
        self.assertIn("-pix_fmt", args)
        self.assertIn("-preset", args)
        p_idx = args.index("-preset")
        self.assertEqual(args[p_idx + 1], "veryfast")
        self.assertIn("boxblur=20:10", str(args))
        self.assertIn("force_original_aspect_ratio=decrease", str(args))

    @patch("app.backend.utils.ffmpeg_wrapper.asyncio.create_subprocess_exec")
    async def test_create_short_video_raises_on_nonzero_returncode(
        self, mock_exec: AsyncMock
    ) -> None:
        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b"ffmpeg error"))
        mock_proc.returncode = 2
        mock_exec.return_value = mock_proc

        from app.backend.utils.ffmpeg_wrapper import FFmpegWrapper

        wrapper = FFmpegWrapper()
        with self.assertRaises(RuntimeError):
            await wrapper.create_short_video(
                img_path="thumb.jpg",
                bgm_path="bgm.mp3",
                out_path="output/short.mp4",
            )

    # --- create_short_thumbnail ---

    @patch("app.backend.utils.ffmpeg_wrapper.asyncio.create_subprocess_exec")
    async def test_create_short_thumbnail_runs_ffmpeg(
        self, mock_exec: AsyncMock
    ) -> None:
        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc

        from app.backend.utils.ffmpeg_wrapper import FFmpegWrapper

        wrapper = FFmpegWrapper()
        await wrapper.create_short_thumbnail(
            img_path="thumb.jpg",
            out_path="output/short_thumb.jpg",
        )

        mock_exec.assert_awaited_once()
        args = mock_exec.call_args[0]
        self.assertIn("output/short_thumb.jpg", args)
        self.assertIn("-vf", args)
        self.assertNotIn("-filter_complex", args)
        self.assertIn("boxblur=20:10", str(args))
        self.assertIn("force_original_aspect_ratio=decrease", str(args))

    @patch("app.backend.utils.ffmpeg_wrapper.asyncio.create_subprocess_exec")
    async def test_create_short_thumbnail_raises_on_nonzero_returncode(
        self, mock_exec: AsyncMock
    ) -> None:
        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b"error"))
        mock_proc.returncode = 1
        mock_exec.return_value = mock_proc

        from app.backend.utils.ffmpeg_wrapper import FFmpegWrapper

        wrapper = FFmpegWrapper()
        with self.assertRaises(RuntimeError):
            await wrapper.create_short_thumbnail(
                img_path="thumb.jpg",
                out_path="output/short_thumb.jpg",
            )


if __name__ == "__main__":
    unittest.main()
