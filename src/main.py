"""Saltwake — a watersports roguelite where the sea remembers.

Audio-first and screen-reader-first, in the tradition of Freight Fate:
Prism speech output (NVDA, JAWS, SAPI, VoiceOver, Speech Dispatcher, and
more via the ``prismatoid`` package), synthesized stereo cues, and a
minimal visual mirror of the last spoken line for sighted players.

Usage:
    python src/main.py              # play
    python src/main.py --self-test  # boot everything headless and exit
    python src/main.py --no-speech  # console speech fallback (development)
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "hide")

import pygame

from core.audio import AudioManager, NullAudio
from core.music import MusicManager, NullMusic
from core.scenes import SceneManager
from core.speech import Speech, NullSpeech
from game import profile as profile_mod
from story.engine import StoryEngine


class GameContext:
    """Everything scenes need: speech, audio, music, profile, story, scenes."""

    def __init__(self, speech, audio, music, profile, story):
        self.speech = speech
        self.audio = audio
        self.music = music
        self.profile = profile
        self.story = story
        self.scenes = SceneManager()
        self.run = None
        self.screen = None


def build_context(no_speech: bool = False, silent: bool = False) -> GameContext:
    profile = profile_mod.load_or_create()
    settings = profile["settings"]
    if silent:
        speech = NullSpeech()
        audio = NullAudio()
        music = NullMusic()
    else:
        speech = Speech(enabled=not no_speech)
        audio = AudioManager(volume=settings.get("audio_volume", 0.5))
        music = MusicManager(volume=settings.get("music_volume", 0.35),
                             enabled=settings.get("music_enabled", True)
                             and audio.enabled)
        speech.adjust_rate(settings.get("speech_rate", 50) - speech.rate)
    story = StoryEngine()
    return GameContext(speech, audio, music, profile, story)


def self_test() -> int:
    """Boots every subsystem headless; exits 0 if the game is assemblable."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.init()
    game = build_context(silent=True)
    arcs = game.story.count_by_arc()
    total = sum(arcs.values())
    assert total >= 140, f"story corpus missing from this build: {total} storylets"
    print(f"Story: {total} storylets across {len(arcs)} arcs: "
          + ", ".join(f"{a}={n}" for a, n in sorted(arcs.items())))
    # Gate the bundle on its data: a build that boots but shipped without
    # these files would fail silently in front of a player instead.
    from game import achievements, almanac
    pages, volumes = almanac.pages(), almanac.volumes()
    assert len(pages) >= 50 and len(volumes) == 5, \
        f"almanac data missing or truncated: {len(pages)} pages, {len(volumes)} volumes"
    achs = achievements.all_achievements()
    assert len(achs) >= 100, f"achievements data missing or truncated: {len(achs)}"
    category_ids = {c["id"] for c in achievements.categories()}
    assert all(a["category"] in category_ids for a in achs)
    print(f"Content: {len(pages)} almanac pages in {len(volumes)} volumes, "
          f"{len(achs)} achievements in {len(category_ids)} categories.")
    from scenes.main_menu import MainMenuScene
    from scenes.harbor import HarborScene
    from game.run import RunState
    from scenes.expedition import ExpeditionScene
    game.scenes.push(MainMenuScene(game))
    game.scenes.push(HarborScene(game))
    run = RunState(game.profile, "skiff", ["shallows"], seed=42)
    game.scenes.push(ExpeditionScene(game, run))
    game.scenes.current.on_enter()
    assert run.chart and run.chart[-1][0]["type"] == "boss"
    print(f"Run: chart of {len(run.chart)} rows generated, hull {run.hull}/{run.hull_max}.")
    print("Self-test passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Saltwake")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--no-speech", action="store_true",
                        help="console speech fallback (development)")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    pygame.init()
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
    except pygame.error as exc:
        print(f"Mixer init failed: {exc}")

    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Saltwake")

    game = build_context(no_speech=args.no_speech)
    game.screen = screen
    font = pygame.font.Font(None, 28)
    title_font = pygame.font.Font(None, 48)

    from scenes.main_menu import MainMenuScene
    game.scenes.push(MainMenuScene(game))

    clock = pygame.time.Clock()
    while game.scenes.running:
        dt = clock.tick(60) / 1000.0
        scene = game.scenes.current
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                profile_mod.save(game.profile)
                game.scenes.quit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_PAGEUP:
                game.speech.say(f"Speech rate {game.speech.adjust_rate(5)}.")
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_PAGEDOWN:
                game.speech.say(f"Speech rate {game.speech.adjust_rate(-5)}.")
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F2:
                on = game.music.toggle()
                game.profile["settings"]["music_enabled"] = on
                game.speech.say(f"Music {'on' if on else 'off'}.")
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_F3, pygame.K_F4):
                delta = -0.05 if event.key == pygame.K_F3 else 0.05
                vol = game.music.set_volume(game.music.volume + delta)
                game.profile["settings"]["music_volume"] = round(vol, 2)
                game.speech.say(f"Music volume {int(vol * 100)} percent.")
            elif scene:
                scene.handle_event(event)
        scene = game.scenes.current
        if scene:
            scene.update(dt)

        # Visual mirror: dark water, title, and the last spoken line.
        screen.fill((6, 18, 34))
        screen.blit(title_font.render("Saltwake", True, (130, 190, 220)), (20, 16))
        last = game.speech.history[-1] if game.speech.history else ""
        y = 80
        for line in _wrap(last, 60):
            screen.blit(font.render(line, True, (220, 230, 235)), (20, y))
            y += 30
        if scene:
            scene.draw(screen)
        pygame.display.flip()

    pygame.quit()
    return 0


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines[:16]


if __name__ == "__main__":
    sys.exit(main())
