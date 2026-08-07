from __future__ import annotations

import json
import os
import time

from google import genai
from google.genai import types

_MODEL = "gemini-3.5-flash"

_SYSTEM_PROMPT = """You extract structured records from meeting transcripts.

Rules:
- Only extract what was actually said. Never invent action items, owners, or dates.
- owner_raw and due_raw must be near-verbatim phrases from the transcript.
- If no due date was mentioned, due_raw is null.
- confidence reflects how explicit the commitment was (below 0.3, consider omitting).
- For "decisions", only include things the room actually agreed on. If people pushed
  back, expressed doubt, or the conversation moved on without real agreement, put
  that under "disagreements" instead - don't flatten it into a decision.
- Respond with ONLY a JSON object. No prose, no markdown fences."""

_SCHEMA_HINT = """{
  "executive_summary": "string, 2-4 sentences",
  "decisions": ["string", ...],
  "disagreements": ["string - where the room did not actually reach consensus", ...],
  "open_questions": ["string", ...],
  "risks": ["string", ...],
  "action_items": [
    {"text": "string", "owner_raw": "string", "due_raw": "string or null", "priority": "low|medium|high", "confidence": 0.0}
  ]
}"""


def extract(transcript_text: str, meeting_date: str, api_key: str | None = None, _retries: int = 3) -> dict:
    client = genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY"))

    user_msg = (
        f"Meeting date: {meeting_date}\n\n"
        f"Transcript:\n{transcript_text}\n\n"
        f"Return JSON matching this schema exactly:\n{_SCHEMA_HINT}"
    )

    last_err = None
    for attempt in range(_retries + 1):
        try:
            resp = client.models.generate_content(
                model=_MODEL,
                contents=user_msg,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
        except Exception as e:
            last_err = e
            wait = 2 ** attempt  # 1s, 2s, 4s, 8s
            print(f"API call failed ({e}), retrying in {wait}s...")
            time.sleep(wait)
            continue

        raw = resp.text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            last_err = ValueError(f"Model did not return valid JSON. Raw output:\n{raw}")
            continue

    raise last_err