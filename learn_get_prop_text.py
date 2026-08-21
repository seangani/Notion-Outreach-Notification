"""
A toy version of get_prop_text, stuffed with print() statements,
so you can watch the decision tree run step by step.
Run this with: python learn_get_prop_text.py
"""


def get_prop_text(prop):
    print(f"\n--- get_prop_text() was called ---")
    print(f"Raw input (prop) = {prop}")

    if prop is None:
        print("prop is None -> returning empty string")
        return ""

    prop_type = prop.get("type")
    print(f"prop_type = '{prop_type}'")

    if prop_type == "title":
        print("Matched the 'title' door.")
        pieces = [t["plain_text"] for t in prop["title"]]
        print(f"Text pieces found: {pieces}")
        result = "".join(pieces)
        print(f"Glued together -> '{result}'")
        return result

    if prop_type == "select":
        print("Matched the 'select' door.")
        if prop["select"]:
            result = prop["select"]["name"]
            print(f"select has a value -> '{result}'")
        else:
            result = ""
            print("select is empty -> ''")
        return result

    if prop_type == "status":
        print("Matched the 'status' door.")
        if prop["status"]:
            result = prop["status"]["name"]
            print(f"status has a value -> '{result}'")
        else:
            result = ""
            print("status is empty -> ''")
        return result

    print("No door matched -> falling through to the final return")
    return ""


# --- Fake Notion data, like what would come back from a real API call ---

fake_name_prop = {"type": "title", "title": [{"plain_text": "Grace Goodley"}]}
fake_stat_prop = {"type": "status", "status": {"name": "2nd Followup"}}
fake_company_prop = {"type": "select", "select": {"name": "Ivo"}}
fake_blank_prop = {"type": "select", "select": None}

print("=" * 50)
print("TEST 1: Name column")
name = get_prop_text(fake_name_prop)
print(f"FINAL VALUE STORED IN 'name' VARIABLE: '{name}'")

print("=" * 50)
print("TEST 2: Stat column")
stat = get_prop_text(fake_stat_prop)
print(f"FINAL VALUE STORED IN 'stat' VARIABLE: '{stat}'")

print("=" * 50)
print("TEST 3: Company column")
company = get_prop_text(fake_company_prop)
print(f"FINAL VALUE STORED IN 'company' VARIABLE: '{company}'")

print("=" * 50)
print("TEST 4: A blank/empty column")
blank = get_prop_text(fake_blank_prop)
print(f"FINAL VALUE STORED IN 'blank' VARIABLE: '{blank}'")

print("=" * 50)
print("Putting it together, the way query_due_rows() does:")
line = f"{name} ({company}) — {stat}"
print(f"due.append(...) would add this line: '{line}'")
