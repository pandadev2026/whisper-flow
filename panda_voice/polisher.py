import logging
import httpx

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a text editor. The user gives you a raw speech transcript.
Your job:
1. Remove filler words (um, uh, like, you know, so, basically, literally, actually, 啊, 嗯, 那个, 就是, 然后 when used as fillers)
2. Fix grammar mistakes and awkward phrasing
3. Edit for clarity and conciseness
4. Preserve the original meaning, tone, and language exactly (Chinese stays Chinese, English stays English, mixed stays mixed)
5. Do NOT add new content or change the intent
Return ONLY the cleaned text, no explanation."""


def polish(
    text: str,
    model: str = "qwen2.5:7b",
    base_url: str = "http://localhost:11434",
) -> str:
    if not text.strip():
        return text
    try:
        resp = httpx.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                "stream": False,
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
    except Exception as e:
        logger.warning("Ollama polish failed, using raw transcript: %s", e)
        return text


def minimax_polish(
    text: str,
    api_key: str,
    group_id: str = "",
    model: str = "MiniMax-Text-01",
    base_url: str = "https://api.minimax.chat/v1",
) -> str:
    if not text.strip():
        return text
    try:
        url = f"{base_url}/chat/completions"
        if group_id:
            url += f"?GroupId={group_id}"
        resp = httpx.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning("MiniMax polish failed, using raw transcript: %s", e)
        return text


def claude_polish(text: str, api_key: str) -> str:
    if not text.strip():
        return text
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        logger.warning("Claude polish failed, using raw transcript: %s", e)
        return text


def warm_up(model: str = "qwen2.5:7b", base_url: str = "http://localhost:11434"):
    """Send a dummy request to load the model into GPU memory before first use."""
    try:
        httpx.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False,
            },
            timeout=30.0,
        )
    except Exception:
        pass
