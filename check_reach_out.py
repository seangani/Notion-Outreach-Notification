import os
import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]

# Which values in the "When to followup?" column should trigger a ping.
# Comma-separated, e.g. "REACH OUT,UPDATE CALL NOTES"
TARGET_VALUES = [v.strip() for v in os.environ.get("TARGET_VALUES", "REACH OUT").split(",")]

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
            name = get_prop_text(props.get("Name"))
            company = get_prop_text(props.get("Company"))
            stat = get_prop_text(props.get("Stat"))
            due.append(f"{name} ({company}) — {stat}")

        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]

    return due


def send_ntfy(lines):
    if not lines:
        print("Nobody due for reach-out right now.")
        return
    message = "\n".join(lines)
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": "Reach out today",
            "Priority": "high",
            "Tags": "email",
        },
    )
    print(f"Pinged ntfy with {len(lines)} people due for reach-out.")


if __name__ == "__main__":
    send_ntfy(query_due_rows())
