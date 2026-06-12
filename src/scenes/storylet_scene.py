"""Plays a storylet: pages are spoken one at a time, then choices offered.

Reading controls: Enter or down arrow advances a page, up arrow re-reads the
previous page, R repeats, Escape skips to the choices (or closes if there are
none). A choice's response is read with the same controls before the scene
closes, so the menu that resumes underneath cannot talk over it. Chained
storylets (goto) play in sequence.
"""

import pygame

from core.menu import AccessibleMenu, MenuItem, BACK
from core.scenes import Scene
from game import profile as profile_mod
from story.effects import apply_effects


class StoryletScene(Scene):
    def __init__(self, game, storylet, run=None, on_close=None):
        super().__init__(game)
        self.storylet = storylet
        self.run = run
        self.on_close = on_close
        self.page_index = 0
        self.mode = "pages"
        self.menu = None
        self.response_lines: list[str] = []
        self.response_index = 0

    def on_enter(self):
        profile_mod.mark_seen(self.game.profile, self.storylet.id)
        msgs = apply_effects(self.storylet.effects, self.game.profile, self.run)
        header = self.storylet.title or "A moment on the water."
        if self.storylet.speaker:
            header = f"{self.storylet.speaker}. {header}"
        # Queue rather than interrupt: storylets start programmatically and
        # may follow an announcement (casting off, a boss intro) mid-speech.
        self.speech.say(header, interrupt=False)
        for m in msgs:
            self.speech.queue(m)
        if self.storylet.pages:
            self.speech.queue(self.storylet.pages[0])
            self.speech.queue("Enter for more.")
        else:
            self._to_choices(interrupt=False)

    def _ctx(self):
        return profile_mod.build_context(self.game.profile, self.run)

    def _to_choices(self, interrupt: bool = True):
        choices = self.game.story.available_choices(
            self.storylet, self._ctx(), self.game.profile["seen_storylets"])
        if not choices:
            self._close()
            return
        self.mode = "choices"
        items = [MenuItem(c["label"], value=i, help_text=c.get("help", ""))
                 for i, c in enumerate(choices)]
        self._choices = choices
        self.menu = AccessibleMenu("What do you do?", items, self.speech, self.audio,
                                   escapable=False)
        self.menu.open(interrupt=interrupt)

    def _choose(self, idx: int):
        choice = self._choices[idx]
        msgs = apply_effects(choice.get("effects", {}), self.game.profile, self.run)
        response = list(choice.get("response", []))
        nxt = self.game.story.get(choice["goto"]) if choice.get("goto") else None
        if nxt:
            for line in response:
                self.speech.queue(line)
            for m in msgs:
                self.speech.queue(m)
            self.storylet = nxt
            self.page_index = 0
            self.mode = "pages"
            self.menu = None
            profile_mod.mark_seen(self.game.profile, nxt.id)
            msgs = apply_effects(nxt.effects, self.game.profile, self.run)
            if nxt.title:
                self.speech.queue(nxt.title)
            for m in msgs:
                self.speech.queue(m)
            if nxt.pages:
                self.speech.queue(nxt.pages[0])
            else:
                self._to_choices(interrupt=False)
            return
        # No follow-up storylet: read the response like pages instead of
        # queueing it and closing, otherwise the menu that resumes under
        # this scene interrupts the response before it is heard.
        lines = response + msgs
        if not lines:
            self._close()
            return
        self.mode = "response"
        self.menu = None
        self.response_lines = lines
        self.response_index = 0
        self.speech.say(lines[0])
        self.speech.queue("Enter for more." if len(lines) > 1 else "Enter to continue.")

    def _close(self):
        self.game.scenes.pop()
        if self.on_close:
            self.on_close()

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if self.mode == "choices":
            result = self.menu.handle_event(event)
            if result is not None and result is not BACK:
                self._choose(result)
            return
        if self.mode == "response":
            self._response_keys(event.key)
            return
        key = event.key
        if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_DOWN):
            self.page_index += 1
            if self.page_index < len(self.storylet.pages):
                self.speech.say(self.storylet.pages[self.page_index])
            else:
                self._to_choices()
        elif key == pygame.K_UP:
            self.page_index = max(0, self.page_index - 1)
            self.speech.say(self.storylet.pages[self.page_index])
        elif key == pygame.K_r:
            self.speech.repeat_last()
        elif key == pygame.K_ESCAPE:
            self._to_choices()

    def _response_keys(self, key):
        if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_DOWN):
            self.response_index += 1
            if self.response_index < len(self.response_lines):
                self.speech.say(self.response_lines[self.response_index])
            else:
                self._close()
        elif key == pygame.K_UP:
            self.response_index = max(0, self.response_index - 1)
            self.speech.say(self.response_lines[self.response_index])
        elif key == pygame.K_r:
            self.speech.repeat_last()
        elif key == pygame.K_ESCAPE:
            self._close()


def maybe_play(game, where: str, run=None, on_close=None) -> bool:
    """Plays the best eligible storylet for a hook point, if any."""
    ctx = profile_mod.build_context(game.profile, run)
    storylet = game.story.pick(where, ctx, game.profile["seen_storylets"])
    if storylet is None:
        return False
    game.scenes.push(StoryletScene(game, storylet, run=run, on_close=on_close))
    return True
