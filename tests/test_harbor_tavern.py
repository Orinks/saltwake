"""The tavern crowd: Liss joins the regulars only once the sea lets her."""

from types import SimpleNamespace

from core.audio import NullAudio
from core.scenes import SceneManager
from core.speech import NullSpeech
from game import profile as profile_mod
from scenes.harbor import HarborScene


def make_scene(profile=None):
    game = SimpleNamespace(speech=NullSpeech(), audio=NullAudio(), music=None,
                           scenes=SceneManager(), profile=profile or profile_mod.new_profile())
    return HarborScene(game)


def tavern_labels(scene):
    scene._tavern_menu()
    return [item.label for item in scene.menu.items]


def test_liss_is_absent_until_saved():
    scene = make_scene()
    labels = tavern_labels(scene)
    assert not any("Liss" in label for label in labels)


def test_liss_holds_court_after_the_finale():
    profile = profile_mod.new_profile()
    profile["qualities"]["liss_saved"] = 1
    scene = make_scene(profile)
    labels = tavern_labels(scene)
    assert any("Liss" in label for label in labels)
    # She joins the crowd, she doesn't displace anyone.
    assert any("Odessa" in label for label in labels)
    assert labels[-1] == "Back to the quay"
