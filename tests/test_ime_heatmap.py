from pathlib import Path

import pytest

from keylab.ime_heatmap import compare_ime_heatmaps, read_lexicon, transform
from keylab.heatmap import kana_to_romaji

ROOT = Path(__file__).parents[1]
LEXICON = ROOT / "lexicons/effiveroman-suffixes.tsv"
LAYOUT = ROOT / "layouts/personal-colemak-derived-65-ue-swap-v2.json"


def test_lexicon_covers_35_with_8_trial():
    entries = read_lexicon(LEXICON)
    assert len(entries) == 35
    assert sum(e["trial"] for e in entries) == 8
    assert len({e["input"] for e in entries}) == 35


def test_normal_preserved_under_no_expansion():
    entries = read_lexicon(LEXICON)
    for phrase in ["がっこう、カタカナ。", "きょうはしゃしんをとります。", "んん", "っして", "ですます"]:
        assert transform(phrase, entries, "none", "double", "x")["keys"] == kana_to_romaji(phrase)[0]


def test_ime_trial_rules():
    entries = read_lexicon(LEXICON)
    result = transform("です。ます。でした。ました。", entries, "trial")
    assert result["keys"] == "ds.ms.dn.mn."
    assert result["saved"] == (4 + 4 + 6 + 6) - 8
    assert result["usage"] == {"dn": 1, "ds": 1, "mn": 1, "ms": 1}


def test_all_replaces_longest_nonoverlapping_suffix():
    entries = read_lexicon(LEXICON)
    result = transform("でございましたら。ませんでした。", entries, "all")
    assert result["keys"] == "pg.bn."
    assert result["usage"] == {"bn": 1, "pg": 1}
    assert transform("でございましたら。", entries, "trial")["usage"] == {"mn": 1}


def test_sokuon_and_small_kana():
    entries = read_lexicon(LEXICON)
    assert transform("っして", entries, "all")["keys"] == "ssite"
    assert transform("ぁゅっ", entries, "none")["keys"] == "lalyultu"


def test_comparison_reports(tmp_path):
    source = tmp_path / "example.txt"
    source.write_text("です。ます。でございましたら。", encoding="utf-8")
    r = compare_ime_heatmaps(source, LAYOUT, LEXICON, tmp_path / "out")
    assert (r["scenarios"]["none"]["estimated_keypresses"] >
            r["scenarios"]["trial"]["estimated_keypresses"] >
            r["scenarios"]["all"]["estimated_keypresses"])
    assert (tmp_path / "out/index.html").exists()
    assert (tmp_path / "out/difference.csv").exists()
    assert (tmp_path / "out/all/heatmap.html").exists()


def test_invalid_mode():
    with pytest.raises(ValueError):
        transform("です", [], "bad")
