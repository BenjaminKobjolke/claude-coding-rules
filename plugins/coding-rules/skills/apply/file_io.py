"""UTF-8 text and JSON file operations used by apply modules."""

import json

def read_text(path):
    return path.read_text(encoding="utf-8")

def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def load_json(path, default):
    if not path.exists():
        return default
    raw = read_text(path)
    if not raw.strip():
        return default
    return json.loads(raw)

def save_json(path, data):
    write_text(path, json.dumps(data, indent=2) + "\n")
