"""FFmpegWrapper: async class wrapping ffmpeg CLI for video/image processing."""

import asyncio
from pathlib import Path


class FFmpegWrapper:
    """Async wrapper around the ffmpeg CLI for video and thumbnail creation.

    All methods invoke ffmpeg as a subprocess and raise RuntimeError on failure.
    9:16 short-form methods apply blur-background scaling to fill the vertical frame.
    """

    # --- Internal helpers ---

    async def _run(self, *args: str) -> None:
        """Execute ffmpeg with the given arguments and raise on nonzero exit.

        Args:
            *args: Individual ffmpeg CLI arguments (excluding the 'ffmpeg' binary).

        Raises:
            RuntimeError: If ffmpeg exits with a nonzero return code.
        """
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"ffmpeg failed (exit {proc.returncode}): {stderr.decode(errors='replace')}"
            )

    # --- Public API ---

    async def create_final_video(
        self, img_path: str, audio_path: str, out_path: str
    ) -> None:
        """Compose a static-image video from a thumbnail and audio track.

        Produces a 16:9 MP4 where the image loops for the full audio duration.

        Args:
            img_path: Path to the source image (JPEG/PNG).
            audio_path: Path to the audio file (MP3/M4A/WAV).
            out_path: Destination path for the rendered MP4.
        """
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        await self._run(
            "-y",
            "-loop",
            "1",
            "-i",
            img_path,
            "-i",
            audio_path,
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-c:a",
            "copy",
            "-pix_fmt",
            "yuv420p",
            "-shortest",
            out_path,
        )

    async def create_short_video(
        self, img_path: str, bgm_path: str, out_path: str
    ) -> None:
        """Compose a 9:16 short-form video from a thumbnail and background music.

        Applies a blurred, scaled version of the image as the full-frame background,
        then overlays a correctly scaled foreground centered on the 9:16 canvas.

        Args:
            img_path: Path to the source thumbnail image.
            bgm_path: Path to the background music file.
            out_path: Destination path for the rendered short MP4.
        """
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        # Canvas: 1080x1920 (9:16)
        # Background: scale-to-fill and blur the source image.
        # Foreground: scale to fit within 1080x1920 canvas, centered.
        vf_filter = (
            "split[v1][v2];"
            "[v1]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,boxblur=20:10[bg];"
            "[v2]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
            "[bg][fg]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2"
        )

        await self._run(
            "-y",
            "-loop",
            "1",
            "-i",
            img_path,
            "-i",
            bgm_path,
            "-vf",
            vf_filter,
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-c:a",
            "copy",
            "-shortest",
            "-pix_fmt",
            "yuv420p",
            out_path,
        )

    async def create_short_thumbnail(self, img_path: str, out_path: str) -> None:
        """Produce a 9:16 thumbnail from a 16:9 source using blur-background scaling.

        Scales the source image to fill a 1080x1920 canvas, blurs it as the
        background, then overlays the correctly scaled foreground centered.

        Args:
            img_path: Path to the source 16:9 thumbnail image.
            out_path: Destination path for the rendered 9:16 image (JPEG/PNG).
        """
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        vf_filter = (
            "split[v1][v2];"
            "[v1]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,boxblur=20:10[bg];"
            "[v2]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
            "[bg][fg]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2"
        )

        await self._run(
            "-y",
            "-i",
            img_path,
            "-vf",
            vf_filter,
            "-frames:v",
            "1",
            out_path,
        )
