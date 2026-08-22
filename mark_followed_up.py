import json
import os
from datetime import date

import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
PAGE_IDS = json.loads(os.environ["PAGE_IDS"])

NOTION_VERSION = "2022-06-28"


def mark_page_contacted_today(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    body = {
        "properties": {
            "Last Contact/Scheduled": {"date": {"start": date.today().isoformat()}}
        }
    }
    resp = requests.patch(url, headers=headers, json=body)
    resp.raise_for_status()


if __name__ == "__main__":
    for page_id in PAGE_IDS:
        mark_page_contacted_today(page_id)
    print(f"Updated Last Contact/Scheduled to today for {len(PAGE_IDS)} people.")
