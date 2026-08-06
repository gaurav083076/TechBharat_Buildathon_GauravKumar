from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Turn:
    speaker: str
    text: str
    start: str | None = None
    end: str | None = None


@dataclass
class Transcript:
    turns: list[Turn] = field(default_factory=list)

    def as_text(self) -> str:
        """Flatten to a speaker-labeled block for LLM consumption."""
        return "\n".join(f"{t.speaker}: {t.text}" for t in self.turns)


_SPEAKER_PREFIX = re.compile(r"^\s*([A-Za-z][A-Za-z .'-]{0,40}):\s*(.*)$")

_SRT_TIME = re.compile(
    r"(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})"
)


def _parse_txt(raw: str) -> Transcript:
    turns: list[Turn] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _SPEAKER_PREFIX.match(line)
        if m:
            turns.append(Turn(speaker=m.group(1).strip(), text=m.group(2).strip()))
        else:
            # Continuation of previous speaker's line, or unlabeled text
            if turns:
                turns[-1].text += " " + line
            else:
                turns.append(Turn(speaker="Unknown", text=line))
    return Transcript(turns=turns)


def _parse_srt_or_vtt(raw: str) -> Transcript:
    turns: list[Turn] = []
    blocks = re.split(r"\n\s*\n", raw.strip())
    for block in blocks:
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        # Drop VTT header / cue-number lines
        lines = [l for l in lines if l.strip().upper() != "WEBVTT" and not l.strip().isdigit()]
        if not lines:
            continue

        start, end = None, None
        text_lines = []
        for l in lines:
            tm = _SRT_TIME.search(l)
            if tm:
                start, end = tm.group(1), tm.group(2)
            else:
                text_lines.append(l)

        text = " ".join(text_lines).strip()
        if not text:
            continue

        m = _SPEAKER_PREFIX.match(text)
        if m:
            speaker, text = m.group(1).strip(), m.group(2).strip()
        else:
            speaker = "Unknown"

        turns.append(Turn(speaker=speaker, text=text, start=start, end=end))
    return Transcript(turns=turns)


def ingest_file(path: str | Path) -> Transcript:
    path = Path(path)
    raw = path.read_text(encoding="utf-8", errors="replace")
    suffix = path.suffix.lower()

    if suffix in (".srt", ".vtt"):
        return _parse_srt_or_vtt(raw)
    return _parse_txt(raw)  # default: treat as plain labeled text