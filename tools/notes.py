import json

def save_info(key, content, source):
    print("TOOL CALL ☎️ save_notes", "arg: ", key, "Sources", source)
    try:
        with open("storage/stored_info.json", "r") as f:
            notes = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        notes = []

    info = {
            "key": key,
            "content": content,
            "source": source,
        }
    
    notes.append(info)

    with open("storage/stored_info.json","w") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)

    return f"Successfully saved info for key {info['key']}"


def read_info(key):
    print("TOOL CALL ☎️ read_info", "arg: ", key)
    try:
        with open("storage/stored_info.json", "r") as f:
            notes = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "Unable to retrieve info"

    required_info = next(
        (info for info in notes if info["key"] == key),
        None
    )

    return required_info