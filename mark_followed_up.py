import json
import os

import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
PAGE_IDS = json.loads(os.environ["PAGE_IDS"])

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
    status = page["properties"]["Stat"]["status"]
    return status["name"] if status else None


def advance_stage(page_id):
    current_stat = get_current_stat(page_id)
    next_stat = NEXT_STAGE.get(current_stat)
    if next_stat is None:
        print(f"Skipping {page_id}: no next stage defined after '{current_stat}'")
        return

    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    body = {"properties": {"Stat": {"status": {"name": next_stat}}}}
    resp = requests.patch(url, headers=headers, json=body)
    resp.raise_for_status()
    print(f"Moved {page_id} from '{current_stat}' to '{next_stat}'")


if __name__ == "__main__":
    for page_id in PAGE_IDS:
        advance_stage(page_id)
