from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from ingest import ingest_file
from extract import extract
from resolve import resolve_date, resolve_owner
from review import review_action_items
from github_integration import create_issue, format_issue_from_action_item
from analytics import compute_analytics

AUDIT_LOG_PATH = "audit_log.jsonl"
PROCESSED_PATH = "processed_items.json"


def run_extraction(transcript_path: str, meeting_date: str, contacts_path: str | None) -> dict:
    transcript = ingest_file(transcript_path)
    if not transcript.turns:
        raise ValueError("No turns parsed from transcript - check file format.")

    record = extract(transcript.as_text(), meeting_date)

    contacts = []
    if contacts_path:
        contacts = json.loads(Path(contacts_path).read_text())

    resolved_items = []
    for item in record.get("action_items", []):
        due_resolved = resolve_date(item.get("due_raw"), meeting_date)
        owner_resolved = resolve_owner(item.get("owner_raw", ""), contacts)

        resolved_items.append({
            **item,
            "due_resolved": due_resolved,
            "due_resolution_failed": item.get("due_raw") is not None and due_resolved is None,
            "owner_resolved": owner_resolved,
            "owner_resolution_failed": owner_resolved is None,
        })

    record["action_items"] = resolved_items
    record["meeting_date"] = meeting_date
    record["source_file"] = transcript_path
    record["analytics"] = compute_analytics(transcript.turns, record)
    return record


def _item_hash(transcript_path: str, item: dict) -> str:
    # Deliberately excludes item["text"] - the LLM's exact wording can vary
    # slightly between calls on the same transcript. Owner + due date + transcript
    # is a stable enough fingerprint for the same real-world commitment.
    key = f"{transcript_path}::{item.get('owner_raw', '').lower().strip()}::{item.get('due_raw')}"
    return hashlib.sha256(key.encode()).hexdigest()


def _load_processed() -> set[str]:
    if not Path(PROCESSED_PATH).exists():
        return set()
    return set(json.loads(Path(PROCESSED_PATH).read_text()))


def _save_processed(processed: set[str]):
    Path(PROCESSED_PATH).write_text(json.dumps(sorted(processed)))


def _append_audit(entry: dict):
    with open(AUDIT_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def create_issues_for_approved(transcript_path: str, repo: str, approved_items: list[dict]):
    processed = _load_processed()

    for item in approved_items:
        h = _item_hash(transcript_path, item)
        if h in processed:
            print(f"Skipping (already created): {item['text']}")
            continue

        title, body = format_issue_from_action_item(item)
        try:
            issue = create_issue(repo, title, body)
        except Exception as e:
            _append_audit({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "create_issue_failed",
                "item_text": item["text"],
                "error": str(e),
            })
            print(f"FAILED to create issue for '{item['text']}': {e}")
            continue

        processed.add(h)
        _append_audit({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "create_issue",
            "item_text": item["text"],
            "owner": item.get("owner_resolved"),
            "due": item.get("due_resolved"),
            "issue_url": issue.get("html_url"),
            "approved_by": "human_via_cli",
        })
        print(f"Created: {issue.get('html_url')}")

    _save_processed(processed)


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Meeting assistant pipeline")
    parser.add_argument("transcript", help="Path to .txt/.vtt/.srt transcript file")
    parser.add_argument("--date", required=True, help="Meeting date, YYYY-MM-DD")
    parser.add_argument("--contacts", default=None, help="Path to contacts JSON")
    parser.add_argument("--repo", default=None, help="owner/repo to create GitHub issues in")
    parser.add_argument("--no-integration", action="store_true", help="Skip review + GitHub, just print extraction")
    args = parser.parse_args()

    try:
        record = run_extraction(args.transcript, args.date, args.contacts)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(record, indent=2))

    if args.no_integration:
        return

    if not args.repo:
        print("\nNo --repo given, skipping review/integration step.")
        return

    approved = review_action_items(record["action_items"])
    print(f"\n{len(approved)} item(s) approved. Creating GitHub issues in {args.repo}...")
    create_issues_for_approved(args.transcript, args.repo, approved)


if __name__ == "__main__":
    main()