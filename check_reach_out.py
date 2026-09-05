import json
import os
import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]

# Which values in the "When to followup?" column should trigger a ping.
# Comma-separated, e.g. "REACH OUT,UPDATE CALL NOTES"
TARGET_VALUES = [v.strip() for v in os.environ.get("TARGET_VALUES", "REACH OUT").split(",")]

# Optional: only needed for the "Mark all as followed up" notification button.
# A fine-grained GitHub token, scoped to just this repo, that's allowed to
# trigger a repository_dispatch event. If it's not set, the button is skipped
# and the notification still sends normally, just without the button.
DISPATCH_TOKEN = os.environ.get("DISPATCH_TOKEN")
GITHUB_REPO = "seangani/Notion-Outreach-Notification"

print("DEBUG: DISPATCH_TOKEN was received:", bool(DISPATCH_TOKEN))

NOTION_VERSION = "2022-06-28"


def get_prop_text(prop):
    """Pull a human-readable string out of any Notion property, regardless of its type."""
    #This code below is needed to skip this logic since there is no data pull till the bottom chunks
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
    if prop_type == "multi_select":
        return ", ".join(o["name"] for o in prop["multi_select"])
    if prop_type == "formula" and prop["formula"]["type"] == "string":
        return prop["formula"]["string"] or ""
    return ""


def query_due_rows():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    payload = {
        "filter": {
            "or": [
                {"property": "When to followup?", "formula": {"string": {"equals": value}}}
                for value in TARGET_VALUES
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
                "stat": get_prop_text(props.get("Stat")),
            })

        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]

    return due


def dispatch_action(label, page_id, target_stat=None):
    client_payload = {"page_ids": [page_id]}
    if target_stat:
        client_payload["target_stat"] = target_stat
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
            "client_payload": client_payload,
        }),
        "clear": True,
    }


def send_ntfy(due):
    if not due:
        print("Nobody due for reach-out right now.")
        return

    for item in due:
        title = f"Reach out: {item['name']} ({item['company']})" if item["company"] else f"Reach out: {item['name']}"
        payload = {
            "topic": NTFY_TOPIC,
            "title": title,
            "message": item["stat"] or "Due for reach-out",
            "priority": 4,
            "tags": ["email"],
        }

        if DISPATCH_TOKEN:
            payload["actions"] = [
                dispatch_action("Mark as followed up", item["id"]),
                dispatch_action("Set up call", item["id"], target_stat="Call Scheduled"),
            ]

        resp = requests.post("https://ntfy.sh/", json=payload)
        resp.raise_for_status()

    print(f"Pinged ntfy with {len(due)} separate notifications.")


if __name__ == "__main__":
    send_ntfy(query_due_rows())
