import logging
from datetime import datetime
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_SYSTEM = """\
You are a meeting notes assistant. Given a raw speech transcript, produce clean, concise meeting notes in Markdown.

Format:
# <inferred topic or "Meeting Notes">

**Date:** <date>

**TL;DR:** One sentence — what was this meeting about and what was the outcome?

## 要点 / Key Points
Cover both discussion points AND decisions in one list. Use as many bullets as needed — more is better.
- Each bullet = one clear, standalone fact, decision, or insight
- Include context so the bullet makes sense on its own
- Merge related items; split unrelated ones

## 待办 / Action Items
- [ ] @owner — what to do (be specific)
- [ ] Unassigned — task (if no owner mentioned)
(Omit this section entirely if no action items were identified)

Rules:
- Match the language of the transcript exactly (Chinese stays Chinese, English stays English, mixed is fine)
- TL;DR must be one sentence, no longer
- Bullet points: prefer more over fewer — capture every meaningful point
- Skip filler, repetition, and off-topic chatter
- If the transcript is too short or unclear, do your best with what's there\
"""


def _save(notes: str, output_dir: str) -> str:
    now = datetime.now()
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    filename = out_path / f"{now.strftime('%Y-%m-%d_%H-%M')}.md"
    filename.write_text(notes, encoding="utf-8")
    logger.info("Meeting notes saved to %s", filename)
    return str(filename)


def _claude_summarize(transcript: str, api_key: str) -> str:
    import anthropic
    now = datetime.now()
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Date: {now.strftime('%Y-%m-%d %H:%M')}\n\nTranscript:\n{transcript}",
            }
        ],
    )
    return message.content[0].text.strip()


def _ollama_summarize(transcript: str, model: str, base_url: str) -> str:
    now = datetime.now()
    resp = httpx.post(
        f"{base_url}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": f"Date: {now.strftime('%Y-%m-%d %H:%M')}\n\nTranscript:\n{transcript}",
                },
            ],
            "stream": False,
        },
        timeout=120.0,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def summarize(
    segments: list[str],
    output_dir: str,
    api_key: str = "",
    ollama_model: str = "qwen2.5:7b",
    ollama_url: str = "http://localhost:11434",
) -> str:
    """Summarize transcript and save Markdown. Uses Claude if api_key set, else Ollama."""
    transcript = "\n\n".join(s for s in segments if s.strip())
    if not transcript:
        raise ValueError("No transcript content to summarize")

    if api_key:
        logger.info("Summarizing with Claude…")
        notes = _claude_summarize(transcript, api_key)
    else:
        logger.info("No API key — summarizing with Ollama (%s)…", ollama_model)
        notes = _ollama_summarize(transcript, ollama_model, ollama_url)

    return _save(notes, output_dir)
