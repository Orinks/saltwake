import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
os.environ.setdefault("SALTWAKE_NO_SPEECH", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
# Point saves at a throwaway dir before core.paths is imported: scenes under
# test save the profile for real, and must never touch the player's saves/.
os.environ.setdefault("SALTWAKE_DATA_DIR",
                      tempfile.mkdtemp(prefix="saltwake-tests-"))
