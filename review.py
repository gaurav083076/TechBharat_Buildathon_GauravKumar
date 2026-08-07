from __future__ import annotations


def review_action_items(action_items: list[dict]) -> list[dict]:
    """
    Walks the user through each action item in the terminal.
    Returns only the approved items (edits applied in place).
    """
    approved = []

    for i, item in enumerate(action_items, 1):
        print(f"\n--- Action item {i}/{len(action_items)} ---")
        print(f"Text:     {item['text']}")
        owner = item.get("owner_resolved")
        print(f"Owner:    {owner['name'] + ' (' + owner['email'] + ')' if owner else 'UNRESOLVED - ' + item.get('owner_raw', '?')}")
        due = item.get("due_resolved")
        print(f"Due:      {due if due else 'UNRESOLVED - ' + str(item.get('due_raw'))}")
        print(f"Priority: {item.get('priority')}")
        print(f"Confidence: {item.get('confidence')}")

        choice = input("\n[a]pprove / [e]dit / [r]eject? ").strip().lower()

        if choice == "r":
            print("Rejected.")
            continue

        if choice == "e":
            new_text = input(f"New text (blank to keep '{item['text']}'): ").strip()
            if new_text:
                item["text"] = new_text
            new_due = input(f"New due date YYYY-MM-DD (blank to keep '{due}'): ").strip()
            if new_due:
                item["due_resolved"] = new_due

        approved.append(item)
        print("Approved.")

    return approved