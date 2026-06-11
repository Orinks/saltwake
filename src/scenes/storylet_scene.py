"""Plays a storylet: pages are spoken one at a time, then choices offered.

Reading controls: Enter or down arrow advances a page, up arrow re-reads the
previous page, R repeats, Escape skips to the choices (or closes if there are
none). Chained storylets (goto) play in sequence.
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
        self.pending_response: list[str] = []

    def on_enter(self):
        profile_mod.mark_seen(self.game.profile, self.storylet.id)
        msgs = apply_effects(self.storylet.effects, self.game.profile, self.run)
        header = self.storylet.title or "A moment on the water."
        if self.storylet.speaker:
            header = f"{self.storylet.speaker}. {header}"
        self.speech.say(header)
        for m in msgs:
            self.speech.queue(m)
        if self.storylet.pages:
            self.speech.queue(self.storylet.pages[0])
            self.speech.queue("Enter for more.")
        else:
            self._to_choices()

    def _ctx(self):
        return profile_mod.build_context(self.game.profile, self.run)

    def _to_choices(self):
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
        self.menu.open()

    def _choose(self, idx: int):
        choice = self._choices[idx]
        msgs = apply_effects(choice.get("effects", {}), self.game.profile, self.run)
        for line in choice.get("response", []):
            self.speech.queue(line)
        for m in msgs:
            self.speech.queue(m)
        goto = choice.get("goto")
        if goto:
            nxt = self.game.story.get(goto)
            if nxt:
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
                    self._to_choices()
                return
        self._close()

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


def maybe_play(game, where: str, run=None, on_close=None) -> bool:
    """Plays the best eligible storylet for a hook point, if any."""
    ctx = profile_mod.build_context(game.profile, run)
    storylet = game.story.pick(where, ctx, game.profile["seen_storylets"])
    if storylet is None:
        return False
    game.scenes.push(StoryletScene(game, storylet, run=run, on_close=on_close))
    return True
