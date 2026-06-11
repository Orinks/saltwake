import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
os.environ.setdefault("SALTWAKE_NO_SPEECH", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
