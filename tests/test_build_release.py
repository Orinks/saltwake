"""Release bundles offer players the manual, not dependency metadata."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import build_release  # noqa: E402

READER_SUFFIXES = (".txt", ".html", ".htm", ".md", ".rst")


def make_bundle(tmp_path):
    """A bundle shaped like PyInstaller's, with the noise it really ships."""
    build = tmp_path / "Saltwake"
    internal = build / "_internal"
    files = {
        "numpy-2.4.6.dist-info/licenses/LICENSE.txt": "numpy BSD text",
        "numpy-2.4.6.dist-info/licenses/numpy/ma/LICENSE": "masked array text",
        "numpy-2.4.6.dist-info/entry_points.txt": "[console_scripts]\nf2py=...",
        "numpy-2.4.6.dist-info/METADATA": "Name: numpy",
        "numpy-2.4.6.dist-info/RECORD": "numpy/__init__.py,,",
        "prismatoid-0.16.5.dist-info/licenses/LICENSES/prism/mpl-2.0.txt": "MPL text",
        "prismatoid-0.16.5.dist-info/licenses/NOTICE": "notice text",
        "sound_lib-0.8.8.dist-info/top_level.txt": "sound_lib",
        "setuptools/_vendor/jaraco/text/Lorem ipsum.txt": "lorem ipsum",
        "_tk_data/license.terms": "Tcl/Tk terms",
        "numpy/_core/_multiarray_umath.pyd": "binary",
        "prism/authors.py": "AUTHORS = []",
        "sound_lib/lib/x64/bass.dll": "binary",
    }
    for name, text in files.items():
        path = internal / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (build / "docs").mkdir()
    (build / "docs" / "Manual.html").write_text("<h1>Saltwake</h1>", encoding="utf-8")
    (build / "LICENSE").write_text("MIT", encoding="utf-8")
    return build


def test_the_manual_is_the_only_document_a_scanner_finds(tmp_path):
    """AGNow lists every .txt and .html in the install folder, so a stray
    entry_points.txt is offered to a player as the game's documentation.
    Licence texts stay in the bundle, extensionless, unlisted."""
    build = make_bundle(tmp_path)
    build_release.consolidate_third_party_licenses(build)

    readable = sorted(p.relative_to(build).as_posix()
                      for p in build.rglob("*")
                      if p.is_file() and p.suffix.lower() in READER_SUFFIXES)
    assert readable == ["docs/Manual.html"]


def test_every_third_party_notice_still_ships(tmp_path):
    """MIT, BSD and Apache all require the notice to travel with the
    binary: the texts may be moved, never dropped."""
    build = make_bundle(tmp_path)
    build_release.consolidate_third_party_licenses(build)

    combined = (build / "Third-Party-Licenses").read_text(encoding="utf-8")
    for text in ("numpy BSD text", "masked array text", "MPL text",
                 "notice text", "Tcl/Tk terms"):
        assert text in combined


def test_code_and_data_are_left_alone(tmp_path):
    """The prune deletes by name, and a module named authors.py once looked
    exactly like an AUTHORS notice."""
    build = make_bundle(tmp_path)
    build_release.consolidate_third_party_licenses(build)

    internal = build / "_internal"
    for name in ("numpy/_core/_multiarray_umath.pyd", "prism/authors.py",
                 "sound_lib/lib/x64/bass.dll", "numpy-2.4.6.dist-info/METADATA",
                 "numpy-2.4.6.dist-info/RECORD"):
        assert (internal / name).exists(), name


def test_emptied_metadata_directories_are_swept_up(tmp_path):
    """A folder left behind still reads as documentation to a player
    browsing the install with a screen reader."""
    build = make_bundle(tmp_path)
    build_release.consolidate_third_party_licenses(build)

    internal = build / "_internal"
    assert not (internal / "numpy-2.4.6.dist-info" / "licenses").exists()
    assert not (internal / "prismatoid-0.16.5.dist-info").exists()
