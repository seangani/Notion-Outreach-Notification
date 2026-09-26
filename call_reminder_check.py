"""
Checks the "Linkdin Outreach" Notion database for calls coming up within the
hour (the "When to followup?" formula shows "CALL REMINDER" for these — see
README) and sends one ntfy push per call, with buttons to log the outcome
once it's done.

Only pings once per call: after sending, this sets "Call Reminder Sent" so
re-runs within the same hour don't duplicate the notification.
"""
import json
import os

import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]

# Optional: same fine-grained GitHub token as check_reach_out.py, allowed to
# trigger a repository_dispatch event. If not set, the notification still
# sends, just without the outcome buttons.
DISPATCH_TOKEN = os.environ.get("DISPATCH_TOKEN")
GITHUB_REPO = "seangani/Notion-Outreach-Notification"

NOTION_VERSION = "2022-06-28"


def get_prop_text(prop):
    """Pull a human-readable string out of any Notion property, regardless of its type."""
    if prop is None:
        return ""
    prop_type = prop.get("type")
    if prop_type == "title":
        return "".join(t["plain_text"] for t in prop["title"])
    if prop_type == "rich_text":
        return "".join(t["plain_text"] for t in prop["rich_text"])
    if prop_type == "select":
        return prop["select"]["name"] if prop["select"] else ""
    if prop_type == "status":
        return prop["status"]["name"] if prop["status"] else ""
    if prop_type == "formula" and prop["formula"]["type"] == "string":
        return prop["formula"]["string"] or ""
    return ""


def query_due_calls():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    payload = {
        "filter": {
            "and": [
                {"property": "When to followup?", "formula": {"string": {"equals": "CALL REMINDER"}}},
                {"property": "Call Reminder Sent", "checkbox": {"equals": False}},
            ]
        }
    }

    due = []
    cursor = None
    while True:
        body = dict(payload)
        if cursor:
            body["start_cursor"] = cursor
        resp = requests.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()

        for page in data["results"]:
            props = page["properties"]
            due.append({
                "id": page["id"],
                "name": get_prop_text(props.get("Name")),
                "company": get_prop_text(props.get("Company")),
            })

        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]

    return due


def mark_reminder_sent(page_id):
    resp = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
        json={"properties": {"Call Reminder Sent": {"checkbox": True}}},
    )
    resp.raise_for_status()


def dispatch_action(label, page_id, target_stat):
    return {
        "action": "http",
        "label": label,
        "url": f"https://api.github.com/repos/{GITHUB_REPO}/dispatches",
        "method": "POST",
        "headers": {
            "Authorization": f"Bearer {DISPATCH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
        "body": json.dumps({
            "event_type": "mark-followed-up",
            "client_payload": {"page_ids": [page_id], "target_stat": target_stat},
        }),
        "clear": True,
    }


def send_ntfy(due):
    if not due:
        print("No calls due for a reminder right now.")
        return

    for item in due:
        title = f"Call soon: {item['name']} ({item['company']})" if item["company"] else f"Call soon: {item['name']}"
        payload = {
            "topic": NTFY_TOPIC,
            "title": title,
            "message": "Coming up within the hour",
            "priority": 5,
            "tags": ["telephone_receiver"],
        }

        if DISPATCH_TOKEN:
            payload["actions"] = [
                dispatch_action("Call finished", item["id"], "Call finished"),
                dispatch_action("Resource for Fulltime", item["id"], "Resource for Fulltime"),
                dispatch_action("Sent Resume", item["id"], "Sent Resume"),
            ]

        resp = requests.post("https://ntfy.sh/", json=payload)
        resp.raise_for_status()
        mark_reminder_sent(item["id"])

    print(f"Pinged ntfy with {len(due)} call reminder(s).")


if __name__ == "__main__":
    send_ntfy(query_due_calls())
