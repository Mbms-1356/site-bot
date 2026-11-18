"""Deterministic 9:16 reel renderer for an educational image plus narration."""
import os
import subprocess
import tempfile
from pathlib import Path


def render_image_reel(image_bytes: bytes, audio_bytes: bytes):
    if not image_bytes or not audio_bytes:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        image = Path(tmp) / 'image.jpg'
        audio = Path(tmp) / 'audio.mp3'
        output = Path(tmp) / 'reel.mp4'
        image.write_bytes(image_bytes)
        audio.write_bytes(audio_bytes)
        cmd = [
            'ffmpeg', '-y', '-loglevel', 'error',
            '-loop', '1', '-i', str(image), '-i', str(audio),
            '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k', '-shortest', '-movflags', '+faststart', str(output),
        ]
        try:
            subprocess.run(cmd, check=True, timeout=180)
            return output.read_bytes() if output.exists() else None
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None
