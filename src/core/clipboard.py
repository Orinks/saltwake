"""System clipboard access for spoken reports.

pygame.scrap is the primary path (it rides SDL's clipboard and works
wherever the game window does, but needs the display to be initialized).
Tk is the fallback for environments where scrap is unavailable, such as
the dummy video driver used by tests and --self-test. Both are best-effort:
callers get a bool and speak success or failure, never a crash.
"""

import logging
import sys

log = logging.getLogger(__name__)


def _copy_scrap(text: str) -> bool:
    import pygame

    if not pygame.display.get_init():
        return False
    if not pygame.scrap.get_init():
        pygame.scrap.init()
    if sys.platform == "win32":
        # scrap stores bytes verbatim; Windows apps expect CRLF and show
        # bare LF as one run-on line
        text = text.replace("\n", "\r\n")
    pygame.scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8"))
    return True


def _copy_tk(text: str) -> bool:
    # Tk applies the platform's line-ending convention itself, so it must
    # be handed plain LF: CRLF in would paste as \r\r\n on Windows.
    import tkinter

    root = tkinter.Tk()
    try:
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()  # hand the clipboard to the OS before Tk goes away
    finally:
        root.destroy()
    return True


def copy_text(text: str) -> bool:
    """Puts ``text`` on the system clipboard. Returns False when no
    clipboard is reachable rather than raising."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for backend in (_copy_scrap, _copy_tk):
        try:
            if backend(text):
                return True
        except Exception:
            log.debug("Clipboard backend %s failed", backend.__name__,
                      exc_info=True)
    return False
