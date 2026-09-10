import json
import os
import urllib.request

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]
PAGE_IDS = json.loads(os.environ["PAGE_IDS"])

# Optional: when set (e.g. "Call Scheduled" from the "Set up call" button),
# jump straight to this stage instead of advancing via NEXT_STAGE below.
TARGET_STAT = os.environ.get("TARGET_STAT") or None

NOTION_VERSION = "2022-06-28"

# Where each stage moves to when you tap "Mark all as followed up."
# Anything not listed here (e.g. "LinkedIn Ghosted", "Call Scheduled") is
# left untouched on purpose, rather than guessing what should come next.
NEXT_STAGE = {
    "First Outreach": "Followup",
    "Followup": "2nd Followup",
    "2nd Followup": "Last Try",
    "Last Try": "Dead",
}


def notion_request(method, url, body=None):
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_current_stat(page_id):
    page = notion_request("GET", f"https://api.notion.com/v1/pages/{page_id}")
    props = page["properties"]

    stat_prop = props["Stat"]
    prop_type = stat_prop["type"]  # e.g. "select" or "status" — read whichever it is
    value = stat_prop[prop_type]
    current_stat = value["name"] if value else None

    title_prop = props.get("Name", {})
    person_name = "".join(t["plain_text"] for t in title_prop.get("title", []))

    return current_stat, prop_type, person_name


def notify(message, tag):
    data = json.dumps({
        "topic": NTFY_TOPIC,
        "title": "Reach-out update",
        "message": message,
        "tags": [tag],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://ntfy.sh/",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req)


def set_stat(page_id, current_stat, next_stat, prop_type):
    body = {"properties": {"Stat": {prop_type: {"name": next_stat}}}}
    notion_request("PATCH", f"https://api.notion.com/v1/pages/{page_id}", body)
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
