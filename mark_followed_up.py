import json
import os

import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]
PAGE_IDS = json.loads(os.environ["PAGE_IDS"])

# Optional: when set (e.g. "Call Scheduled" from the "Set up call" button),
# jump straight to this stage instead of advancing via NEXT_STAGE below.
TARGET_STAT = os.environ.get("TARGET_STAT") or None

NOTION_VERSION = "2022-06-28"

# Where each stage moves to when you tap "Mark all as followed up."
# Anything not listed here (e.g. "Last Try", "LinkedIn Ghosted", "Call
# Scheduled") is left untouched on purpose, rather than guessing what
# should come next.
NEXT_STAGE = {
    "First Outreach": "Followup",
    "Followup": "2nd Followup",
    "2nd Followup": "Last Try",
}


def get_current_stat(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    page = resp.json()
    props = page["properties"]

    stat_prop = props["Stat"]
    prop_type = stat_prop["type"]  # e.g. "select" or "status" — read whichever it is
    value = stat_prop[prop_type]
    current_stat = value["name"] if value else None

    title_prop = props.get("Name", {})
    person_name = "".join(t["plain_text"] for t in title_prop.get("title", []))

    return current_stat, prop_type, person_name


def notify(message, tag):
    requests.post(
        "https://ntfy.sh/",
        json={"topic": NTFY_TOPIC, "title": "Reach-out update", "message": message, "tags": [tag]},
    )


def set_stat(page_id, current_stat, next_stat, prop_type):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    body = {"properties": {"Stat": {prop_type: {"name": next_stat}}}}
    resp = requests.patch(url, headers=headers, json=body)
    resp.raise_for_status()
    print(f"Moved {page_id} from '{current_stat}' to '{next_stat}'")


def advance_stage(page_id):
    # Always re-check the live value in Notion right now, rather than
    # trusting whatever the stage was back when the notification was sent —
    # this protects any manual edits you made in the meantime (e.g.
    # changing someone to "LinkedIn Ghosted") from being overwritten.
    current_stat, prop_type, person_name = get_current_stat(page_id)

    if TARGET_STAT is not None:
        set_stat(page_id, current_stat, TARGET_STAT, prop_type)
        notify(f"{person_name}: now '{TARGET_STAT}'", "white_check_mark")
        return

    next_stat = NEXT_STAGE.get(current_stat)
    if next_stat is None:
        print(f"Skipping {page_id}: no next stage defined after '{current_stat}'")
        notify(f"{person_name}: nothing to advance to after '{current_stat}'", "warning")
        return

    set_stat(page_id, current_stat, next_stat, prop_type)
    notify(f"{person_name}: '{current_stat}' -> '{next_stat}'", "white_check_mark")


if __name__ == "__main__":
    for page_id in PAGE_IDS:
        try:
            advance_stage(page_id)
        except Exception as e:
            notify(f"Failed to update page {page_id}: {e}", "x")
            raise

