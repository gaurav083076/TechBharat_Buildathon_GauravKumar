from __future__ import annotations

import json
import os

from anthropic import Anthropic

_MODEL = "claude-sonnet-4-6"

_SYSTEM_PROMPT = """You extract structured records from meeting transcripts.

Rules:
- Only extract what was actually said. Never invent action items, owners, or dates.
- owner_raw and due_raw must be near-verbatim phrases from the transcript.
- If no due date was mentioned, due_raw is null.
- confidence reflects how explicit the commitment was (below 0.3, consider omitting).
- Respond with ONLY a JSON object. No prose, no markdown fences."""

_SCHEMA_HINT = """{
  "executive_summary": "string, 2-4 sentences",
  "decisions": ["string", ...],
  "open_questions": ["string", ...],
  "risks": ["string", ...],
  "action_items": [
    {"text": "string", "owner_raw": "string", "due_raw": "string or null", "priority": "low|medium|high", "confidence": 0.0}
  ]
}"""


def extract(transcript_text: str, meeting_date: str, api_key: str | None = None) -> dict:
    client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    user_msg = (
        f"Meeting date: {meeting_date}\n\n"
        f"Transcript:\n{transcript_text}\n\n"
        f"Return JSON matching this schema exactly:\n{_SCHEMA_HINT}"
    )

    resp = client.messages.create(
        model=_MODEL,
        max_tokens=2000,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON. Raw output:\n{raw}") from e