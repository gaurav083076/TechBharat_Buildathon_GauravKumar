from __future__ import annotations

from collections import Counter


def compute_analytics(turns: list, record: dict) -> dict:
    """
    turns: list of Turn objects from ingest.py (has .speaker, .text)
    record: the structured record from extract.py (has decisions, action_items, etc.)
    """
    word_counts = Counter()
    turn_counts = Counter()

    for t in turns:
        word_counts[t.speaker] += len(t.text.split())
        turn_counts[t.speaker] += 1

    total_words = sum(word_counts.values())
    talk_time_pct = {
        speaker: round(100 * count / total_words, 1) if total_words else 0
        for speaker, count in word_counts.items()
    }

    return {
        "talk_time_by_speaker_pct": talk_time_pct,
        "turn_count_by_speaker": dict(turn_counts),
        "decision_count": len(record.get("decisions", [])),
        "action_item_count": len(record.get("action_items", [])),
        "risk_count": len(record.get("risks", [])),
        "open_question_count": len(record.get("open_questions", [])),
    }