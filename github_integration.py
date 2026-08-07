from __future__ import annotations

import os

import requests

_API_BASE = "https://api.github.com"


def create_issue(repo: str, title: str, body: str, token: str | None = None) -> dict:
    """
    repo: "owner/reponame", e.g. "gaurav083076/meeting-assistant-sandbox"
    Returns the created issue's data (includes "html_url", "number").
    Raises on failure - caller should catch and log to the audit trail.
    """
    token = token or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN not set")

    url = f"{_API_BASE}/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    payload = {"title": title, "body": body}

    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def format_issue_from_action_item(item: dict) -> tuple[str, str]:
    """Turns a resolved action item dict into (title, body) for a GitHub issue."""
    title = item["text"]

    owner = item.get("owner_resolved")
    owner_line = f"**Owner:** {owner['name']} ({owner['email']})" if owner else "**Owner:** unresolved"

    due = item.get("due_resolved") or "not specified"

    body = (
        f"{owner_line}\n"
        f"**Due:** {due}\n"
        f"**Priority:** {item.get('priority', 'unspecified')}\n"
        f"**Confidence:** {item.get('confidence', 'n/a')}\n\n"
        f"_Created from meeting transcript, {item.get('due_raw', 'no due date mentioned')}._"
    )
    return title, body