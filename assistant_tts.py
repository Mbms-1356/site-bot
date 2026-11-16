"""Small Persian TTS helper shared by the signal and site bots."""
import asyncio
import io


def synthesize_fa(text: str):
    text = (text or '').strip()
    if not text:
        return None
    try:
        import edge_tts

        async def render():
            output = io.BytesIO()
            communicate = edge_tts.Communicate(text[:3500], 'fa-IR-DilaraNeural')
            async for chunk in communicate.stream():
                if chunk.get('type') == 'audio':
                    output.write(chunk['data'])
            output.seek(0)
            return output

        return asyncio.run(render())
    except Exception:
        return None
