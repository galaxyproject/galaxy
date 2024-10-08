

def collate_table(path: str) -> list:
    with open(path, "r") as f:
        contents = f.read()
    first_options = []
    second_options = []
    values = [
        {"name": "First Column", "value": "first", "selected": False, "options": first_options},
        {"name": "Second Column", "value": "second", "selected": False, "options": second_options},
    ]
    seen_in_column_1 = set()
    seen_in_column_2 = set()
    for line in contents.splitlines():
        parts = line.split("\t")
        if len(parts) >= 1:
            val = parts[0]
            if val not in seen_in_column_1:
                first_options.append({"name": val.upper(), "value": val, "selected": False, "options": []})
                seen_in_column_1.add(val)
        if len(parts) >= 2:
            val = parts[1]
            if val not in seen_in_column_2:
                second_options.append({"name": val.upper(), "value": val, "selected": False, "options": []})
                seen_in_column_2.add(val)
    return values
