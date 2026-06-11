"""Scene stack manager.

Each screen of the game (menus, harbor, expedition chart, activities, story
events) is a Scene. The manager keeps a stack so nested screens return to
their parent naturally (settings over harbor, event over chart, and so on).
"""

from typing import Optional


class Scene:
    def __init__(self, game):
        self.game = game  # GameContext: speech, audio, profile, run, etc.

    @property
    def speech(self):
        return self.game.speech

    @property
    def audio(self):
        return self.game.audio

    def on_enter(self) -> None:
        """Called when the scene becomes the active (top) scene."""

    def on_exit(self) -> None:
        """Called when the scene is removed from the stack."""

    def on_resume(self) -> None:
        """Called when a scene above this one was popped. Default: no-op,
        because most flows continue via explicit callbacks."""

    def handle_event(self, event) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, screen) -> None:
        pass


class SceneManager:
    def __init__(self):
        self.stack: list[Scene] = []
        self.running = True

    @property
    def current(self) -> Optional[Scene]:
        return self.stack[-1] if self.stack else None

    def push(self, scene: Scene) -> None:
        self.stack.append(scene)
        scene.on_enter()

    def pop(self) -> Optional[Scene]:
        if not self.stack:
            return None
        top = self.stack.pop()
        top.on_exit()
        if self.stack:
            self.stack[-1].on_resume()
        else:
            self.running = False
        return top

    def replace(self, scene: Scene) -> None:
        if self.stack:
            old = self.stack.pop()
            old.on_exit()
        self.stack.append(scene)
        scene.on_enter()

    def clear_and_push(self, scene: Scene) -> None:
        while self.stack:
            self.stack.pop().on_exit()
        self.push(scene)

    def quit(self) -> None:
        while self.stack:
            self.stack.pop().on_exit()
        self.running = False
