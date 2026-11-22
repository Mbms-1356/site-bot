"""Deterministic 9:16 reel renderer for educational image + narration."""
import re
import subprocess
import tempfile
from pathlib import Path


def _srt_timestamp(seconds: float) -> str:
    ms = int(max(0, seconds) * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def _srt_text(text: str, duration: float = 45.0) -> str:
    clean = re.sub(r'[\r\n]+', ' ', text or '').strip()
    clean = re.sub(r'\s+', ' ', clean)
    words = clean.split()
    lines, current = [], ''
    for word in words:
        if len(current) + len(word) + 1 > 38 and current:
            lines.append(current)
            current = word
        else:
            current = (current + ' ' + word).strip()
    if current:
        lines.append(current)
    lines = lines[:24]
    if not lines:
        return ''
    block = duration / len(lines)
    chunks = []
    for i, line in enumerate(lines):
        start = i * block
        end = duration if i == len(lines) - 1 else (i + 1) * block
        chunks.append(f'{i + 1}\n{_srt_timestamp(start)} --> {_srt_timestamp(end)}\n{line}\n')
    return '\n'.join(chunks) + '\n'


def render_image_reel(image_bytes: bytes, audio_bytes: bytes, caption_text: str = ''):
    if not image_bytes or not audio_bytes:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        image = Path(tmp) / 'image.jpg'
        audio = Path(tmp) / 'audio.mp3'
        srt = Path(tmp) / 'captions.srt'
        output = Path(tmp) / 'reel.mp4'
        image.write_bytes(image_bytes)
        audio.write_bytes(audio_bytes)
        subtitle_filter = ''
        if caption_text:
            srt.write_text(_srt_text(caption_text, 45.0), encoding='utf-8')
            subtitle_filter = ",subtitles='" + str(srt).replace("'", "\\'") + "':force_style='FontName=DejaVu Sans,FontSize=26,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Alignment=2,MarginV=70'"
        vf = ("scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,"
              "zoompan=z='min(zoom+0.0007,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=720x1280:fps=30,format=yuv420p" + subtitle_filter)
        cmd = [
            'ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-i', str(image), '-i', str(audio),
            '-vf', vf, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28',
            '-c:a', 'aac', '-b:a', '96k', '-af', 'apad', '-t', '45',
            '-movflags', '+faststart', str(output),
        ]
        try:
            subprocess.run(cmd, check=True, timeout=180)
            return output.read_bytes() if output.exists() else None
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None
