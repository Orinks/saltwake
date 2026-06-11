"""Screen reader output via Prism (the ``prismatoid`` package).

Prism is a screen reader abstraction layer that unifies NVDA, JAWS, SAPI,
VoiceOver, Speech Dispatcher, and many other backends behind one API — the
same integration Freight Fate uses. This module wraps it in a small
game-friendly interface that:

* never crashes the game if speech is unavailable (console fallback),
* picks the best backend that is actually usable on this machine: Prism's
  registry lists every backend it was compiled with (NVDA first by static
  priority) whether or not that screen reader is running, so the choice is
  validated against ``is_supported_at_runtime`` and falls down the priority
  list instead of binding to a screen reader that is not there,
* prefers ``output`` (speech + braille) and falls back to ``speak``,
* can be disabled with the ``SALTWAKE_NO_SPEECH=1`` environment variable
  (used by the headless test suite) and forced to a specific backend with
  ``SALTWAKE_SPEECH_BACKEND=<name>`` (for example ``SAPI``),
* keeps a history buffer so the player can replay announcements (R key).
"""

from __future__ import annotations

import logging
import os
from collections import deque

log = logging.getLogger(__name__)


def _usable(backend) -> bool:
    """True when the backend can actually speak on this machine right now."""
    try:
        features = backend.features
    except Exception:
        return False
    return bool(features.is_supported_at_runtime
                and (features.supports_output or features.supports_speak))


def pick_backend(ctx, override: str | None = None):
    """Choose a speech backend from a Prism context.

    ``acquire_best`` ranks by static registry priority, which can return a
    screen reader that is installed in the registry but not running (NVDA
    outranks everything). Validate its runtime support, then fall back
    through the remaining backends in priority order. Returns None when
    nothing on the machine can speak.
    """
    if override:
        try:
            backend = ctx.acquire(ctx.id_of(override))
            if _usable(backend):
                return backend
            log.warning("Requested speech backend %s is not usable; "
                        "falling back to automatic choice", override)
        except Exception:
            log.warning("Requested speech backend %s not found; "
                        "falling back to automatic choice", override,
                        exc_info=True)
    try:
        best = ctx.acquire_best()
        if _usable(best):
            return best
        log.info("Prism's preferred backend %s is not running; "
                 "trying the others", getattr(best, "name", "?"))
    except Exception:
        log.debug("acquire_best failed", exc_info=True)
    try:
        ids = [ctx.id_of(i) for i in range(ctx.backends_count)]
        ids.sort(key=ctx.priority_of, reverse=True)
    except Exception:
        log.warning("Could not enumerate speech backends", exc_info=True)
        return None
    for backend_id in ids:
        try:
            backend = ctx.acquire(backend_id)
        except Exception:
            continue
        if _usable(backend):
            return backend
    return None


class Speech:
    """Speech output channel for the whole game.

    All game text flows through :meth:`say`. ``interrupt=True`` (the default)
    cuts off the previous utterance, which is what menu navigation wants;
    use :meth:`queue` for follow-on announcements.
    """

    HISTORY_SIZE = 30

    def __init__(self, enabled: bool = True):
        self.history: deque[str] = deque(maxlen=self.HISTORY_SIZE)
        self.rate = 50
        self.status = "disabled"
        self._ctx = None
        self._backend = None
        self._prism_error: type[Exception] = Exception
        self._echo = False
        if not enabled:
            self._echo = True
            self.status = "console"
            return
        if os.environ.get("SALTWAKE_NO_SPEECH"):
            log.info("Speech disabled via SALTWAKE_NO_SPEECH")
            return
        try:
            import prism

            self._ctx = prism.Context()
            self._backend = pick_backend(
                self._ctx, os.environ.get("SALTWAKE_SPEECH_BACKEND"))
            self._prism_error = prism.PrismError
            if self._backend is None:
                log.warning("No usable speech backend on this machine; "
                            "echoing to console")
                self._ctx = None
                self._echo = True
                self.status = "fallback"
            else:
                log.info("Speech backend: %s", self._backend.name)
                self.status = "active"
        except Exception:
            log.exception("Prism unavailable; echoing to console")
            self._ctx = None
            self._backend = None
            self._echo = True
            self.status = "fallback"

    @property
    def available(self) -> bool:
        return self._backend is not None

    @property
    def backend_name(self) -> str:
        if self._backend is None:
            return "none"
        try:
            return self._backend.name
        except Exception:
            return "unknown"

    def _emit(self, text: str, interrupt: bool) -> None:
        if self._echo:
            print(f"[speech] {text}")
            return
        if self._backend is None:
            return
        try:
            features = self._backend.features
            if features.supports_output:
                self._backend.output(text, interrupt)
            elif features.supports_speak:
                self._backend.speak(text, interrupt)
        except self._prism_error:
            log.warning("Speech output failed", exc_info=True)
        except Exception:
            log.exception("Unexpected speech failure; disabling speech")
            self._backend = None
            self._echo = True

    def say(self, text: str, interrupt: bool = True) -> None:
        if not text:
            return
        self.history.append(text)
        self._emit(text, interrupt)

    def queue(self, text: str) -> None:
        """Speak without interrupting current speech."""
        self.say(text, interrupt=False)

    def repeat_last(self, count: int = 1) -> None:
        if not self.history:
            self.say("Nothing to repeat.")
            return
        items = list(self.history)[-count:]
        # Re-speak without polluting history with duplicates.
        self._emit(" ".join(items), True)

    def stop(self) -> None:
        """Silence any in-progress speech."""
        if self._backend is None:
            return
        try:
            if self._backend.features.supports_stop:
                self._backend.stop()
        except Exception:
            pass

    def adjust_rate(self, delta: int) -> int:
        """Rate is owned by the screen reader with most backends; apply it
        where Prism exposes it and remember the preference either way."""
        self.rate = max(0, min(100, self.rate + delta))
        backend = self._backend
        if backend is not None:
            try:
                if getattr(backend.features, "supports_rate", False):
                    backend.set_rate(self.rate)
            except Exception:
                pass
        return self.rate

    def shutdown(self) -> None:
        """Release the backend and context. Safe to call more than once."""
        self.stop()
        self._backend = None
        self._ctx = None


class NullSpeech(Speech):
    """Silent speech engine for tests."""

    def __init__(self):
        self.history = deque(maxlen=self.HISTORY_SIZE)
        self.rate = 50
        self.status = "disabled"
        self._ctx = None
        self._backend = None
        self._prism_error = Exception
        self._echo = False

    def say(self, text: str, interrupt: bool = True) -> None:
        if text:
            self.history.append(text)

    def repeat_last(self, count: int = 1) -> None:
        pass

    def adjust_rate(self, delta: int) -> int:
        return self.rate
