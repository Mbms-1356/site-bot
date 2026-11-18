"""Deterministic 9:16 reel renderer for educational image + narration."""
import re
import subprocess
import tempfile
from pathlib import Path


def _srt_text(text: str) -> str:
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
    return '1\n00:00:00,000 --> 99:59:59,000\n' + '\n'.join(lines[:8]) + '\n\n'


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
            srt.write_text(_srt_text(caption_text), encoding='utf-8')
            subtitle_filter = ",subtitles='" + str(srt).replace("'", "\\'") + "':force_style='FontName=DejaVu Sans,FontSize=26,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Alignment=2,MarginV=70'"
        vf = ("scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,"
              "zoompan=z='min(zoom+0.0007,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=720x1280:fps=30,format=yuv420p" + subtitle_filter)
        cmd = [
            'ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-i', str(image), '-i', str(audio),
            '-vf', vf, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28',
            '-c:a', 'aac', '-b:a', '96k', '-shortest', '-movflags', '+faststart', str(output),
        ]
        try:
            subprocess.run(cmd, check=True, timeout=180)
            return output.read_bytes() if output.exists() else None
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None
