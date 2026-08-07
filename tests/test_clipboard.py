"""Line endings on the clipboard, per platform.

pygame.scrap stores bytes verbatim, so Windows needs CRLF or every app
pastes the report as one run-on line. Tk converts newlines itself, so it
must be handed plain LF or Windows pastes come out with \r\r\n.
"""

import pygame

from core import clipboard


def _capture_scrap(monkeypatch):
    got = []
    monkeypatch.setattr(pygame.display, "get_init", lambda: True)
    monkeypatch.setattr(pygame.scrap, "get_init", lambda: True)
    monkeypatch.setattr(pygame.scrap, "put",
                        lambda fmt, data: got.append((fmt, data)))
    return got


def test_copy_text_normalizes_mixed_endings_before_the_backends(monkeypatch):
    got = []
    monkeypatch.setattr(clipboard, "_copy_scrap",
                        lambda t: got.append(t) or True)
    assert clipboard.copy_text("a\r\nb\rc\nd")
    assert got == ["a\nb\nc\nd"]


def test_scrap_stores_crlf_on_windows(monkeypatch):
    got = _capture_scrap(monkeypatch)
    monkeypatch.setattr(clipboard.sys, "platform", "win32")
    assert clipboard._copy_scrap("Renown: 3\nPears: 4")
    assert got == [(pygame.SCRAP_TEXT, b"Renown: 3\r\nPears: 4")]


def test_scrap_keeps_lf_on_other_platforms(monkeypatch):
    got = _capture_scrap(monkeypatch)
    monkeypatch.setattr(clipboard.sys, "platform", "darwin")
    assert clipboard._copy_scrap("Renown: 3\nPears: 4")
    assert got == [(pygame.SCRAP_TEXT, b"Renown: 3\nPears: 4")]


def test_tk_fallback_is_handed_plain_lf_even_on_windows(monkeypatch):
    got = []
    monkeypatch.setattr(clipboard, "_copy_scrap", lambda t: False)
    monkeypatch.setattr(clipboard, "_copy_tk",
                        lambda t: got.append(t) or True)
    monkeypatch.setattr(clipboard.sys, "platform", "win32")
    assert clipboard.copy_text("Renown: 3\r\nPears: 4")
    assert got == ["Renown: 3\nPears: 4"]
