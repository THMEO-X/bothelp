import json
import os

STORAGE_FILE = "data.json"

def load_data():
    if not os.path.exists(STORAGE_FILE):
        return {}
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_data(data: dict):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get(key, default=None):
    data = load_data()
    return data.get(key, default)

def set(key, value):
    data = load_data()
    data[key] = value
    save_data(data)

def delete(key):
    data = load_data()
    if key in data:
        del data[key]
        save_data(data)