# Meeting Assistant - TechBharat Buildathon

Use Case B - Agentic AI Meeting Assistant

Takes a meeting transcript, pulls out the summary, decisions, risks and action items,
resolves owners/due dates, and after you approve it creates real GitHub issues for
the approved items.

Working and tested:
- reads .txt/.vtt/.srt transcripts
- extraction via Gemini - summary, decisions, disagreements, open questions, risks, action items
- resolves "next Friday" type dates into real dates, matches owner names to contacts
- if it can't confidently resolve a date or owner it flags it instead of guessing
- review step in the terminal - approve, edit or reject each item before anything happens
- creates GitHub issues for approved items
- audit log of what got created and why
- checked idempotency - running the same transcript twice doesn't duplicate issues
- ran it against a ~5,500 word, 26-action-item, 4-speaker transcript, finished in 43 seconds, well under the 5 min limit
- disagreement detection - separates things the room actually agreed on from things someone pushed back on, instead of flattening everything into a decision
- meeting analytics - talk time per speaker, decision/action item/risk counts
- evidence links - every action item traces back to the exact transcript turn it came from, with a real timestamp for .vtt/.srt input
- handles Hindi-English code-switched speech correctly with no extra code, since the underlying LLM already understands mixed-language input natively

## Running it

```
pip install -r requirements.txt
```

add a `.env` with `GEMINI_API_KEY` and `GITHUB_TOKEN`

```
python3 main.py sample_data/meeting.txt --date 2026-08-06 --contacts sample_data/contacts.json --repo <owner/repo>
```

It prints the extracted record, then walks through each action item asking approve/edit/reject,
then creates GitHub issues for whatever got approved.

## Testing commands

Core extraction only, no review/GitHub step:
```
python3 main.py sample_data/meeting.txt --date 2026-08-06 --contacts sample_data/contacts.json --no-integration
```

Full flow with human review and real GitHub issue creation:
```
python3 main.py sample_data/meeting.txt --date 2026-08-06 --contacts sample_data/contacts.json --repo <owner/repo>
```

Run the same command again to check idempotency - approving the same item a second time
should print "Skipping (already created)" instead of making a new issue.

Check the audit log after creating issues:
```
cat audit_log.jsonl
```

Latency test on a longer, more complex transcript:
```
time python3 main.py sample_data/long_meeting.txt --date 2026-08-06 --contacts sample_data/contacts.json --no-integration
```

Code-switched Hindi-English transcript:
```
python3 main.py sample_data/code_switched_meeting.txt --date 2026-08-06 --contacts sample_data/contacts.json --no-integration
```

## Output proof

Annotated screenshots of the above tests, run and verified: https://excalidraw.com/#json=s3C-wkk8DQcsZBg-3Sl5f,Aw5n8uxtHWFvncdZuBfT1A

## Files

- `ingest.py` - parses the transcript file
- `extract.py` - calls Gemini, gets back structured JSON
- `resolve.py` - turns raw dates/owners into real dates and contacts
- `review.py` - the approve/edit/reject step
- `github_integration.py` - creates the actual issues
- `analytics.py` - talk time and count stats from a meeting
- `main.py` - ties it all together, handles the audit log + duplicate checking
- `sample_data/` - test transcripts and contacts:
  - `meeting.txt` - short sample transcript, pricing page redesign discussion, 2 speakers, 2 action items
  - `long_meeting.txt` - ~5,500 word, 4-speaker, 26-action-item transcript, used for the latency test
  - `code_switched_meeting.txt` - Hindi-English mixed standup transcript, used to test code-switched speech handling
  - `contacts.json` - sample contact list (Priya, Amit, Sana, Rahul) used for owner resolution