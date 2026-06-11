import os

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(SRC_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
STORY_DIR = os.path.join(DATA_DIR, "story")
SAVE_DIR = os.path.join(PROJECT_ROOT, "saves")


def ensure_save_dir() -> str:
    os.makedirs(SAVE_DIR, exist_ok=True)
    return SAVE_DIR
