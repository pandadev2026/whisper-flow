import logging
from datetime import datetime
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

_SYSTEM = """\
You are a professional meeting notes assistant. Given a raw speech transcript, produce structured meeting notes in Markdown.

Format:
# <inferred title or "Meeting Notes">

**Date:** <date>

## Summary
2-3 sentence overview.

## Key Discussion Points
- bullet points

## Action Items
- [ ] task — @owner (if mentioned)

## Decisions Made
- bullet points

Rules:
- Match the language of the transcript (Chinese stays Chinese, English stays English, mixed is fine)
- Be concise and professional
- If the transcript is too short or unclear, do your best with what's there\
"""


def summarize(segments: list[str], api_key: str, output_dir: str) -> str:
    """Summarize transcript segments with Claude and save to output_dir. Returns saved file path."""
    transcript = "\n\n".join(s for s in segments if s.strip())
    if not transcript:
        raise ValueError("No transcript content to summarize")

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
    notes = message.content[0].text.strip()

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    filename = out_path / f"{now.strftime('%Y-%m-%d_%H-%M')}.md"
    filename.write_text(notes, encoding="utf-8")
    logger.info("Meeting notes saved to %s", filename)
    return str(filename)
