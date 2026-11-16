"""Safe local extraction helpers for content-factory uploads."""
import io
import re
import zipfile
from pathlib import Path


def extract_text(data: bytes, name: str) -> str:
    lower = (name or '').lower()
    if lower.endswith('.pdf'):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            return '\n'.join((page.extract_text() or '') for page in reader.pages[:30])[:30000]
        except Exception:
            return ''
    if lower.endswith('.docx'):
        try:
            z = zipfile.ZipFile(io.BytesIO(data))
            raw = z.read('word/document.xml').decode('utf-8', 'ignore')
            raw = raw.replace('</w:p>', '\n')
            return re.sub(r'<[^>]+>', ' ', raw)[:30000]
        except Exception:
            return ''
    if lower.endswith(('.txt', '.md', '.rtf')):
        for encoding in ('utf-8', 'cp1256', 'latin-1'):
            try:
                text = data.decode(encoding)
                if lower.endswith('.rtf'):
                    text = re.sub(r'\\[a-z]+-?\d* ?', '', text)
                    text = re.sub(r'[{}]', '', text)
                return text[:30000]
            except Exception:
                continue
    return ''


def classify(name: str, kind: str = '') -> str:
    lower = (name or '').lower()
    if kind == 'photo' or lower.endswith(('.jpg', '.jpeg', '.png', '.webp')):
        return 'image'
    if kind in ('audio', 'voice') or lower.endswith(('.mp3', '.m4a', '.wav', '.ogg')):
        return 'audio'
    if kind == 'video' or lower.endswith(('.mp4', '.mov', '.mkv', '.webm')):
        return 'video'
    if lower.endswith(('.pdf', '.docx', '.txt', '.md', '.rtf')):
        return 'document'
    return 'unknown'
