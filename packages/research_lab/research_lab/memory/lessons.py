from __future__ import annotations
import json
import os
from typing import Dict, Any

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..", "data", "artifacts"))
LESSONS_PATH = os.path.join(DATA_DIR, "lessons.jsonl")

os.makedirs(DATA_DIR, exist_ok=True)

def record_lesson(lesson: Dict[str, Any]) -> None:
    with open(LESSONS_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(lesson) + "\n")
