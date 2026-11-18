import csv
import json
from pathlib import Path

import pytest

from keylab.heatmap import calculate, generate_heatmap, get_keystrokes, kana_to_romaji, load_layout

LAYOUT = Path(__file__).parents[1] / "layouts" / "personal-colemak-derived-65.json"

def test_kana_ime():
    result, skipped = kana_to_romaji("きょうはしゃしんをとります。")
    assert result == "kyouhasyasinnwotorimasu."
    assert not skipped

def test_sokuon_and_katakana():
    result, skipped = get_keystrokes("がっこう、カタカナ。", mode="kana")
    assert result == "gakkou,katakana."
    assert not skipped

def test_n_style():
    assert kana_to_romaji("かんじ")[0] == "kannzi"
    assert kana_to_romaji("かんじ", "contextual")[0] == "kanzi"
    assert kana_to_romaji("しんよう", "contextual")[0] == "sinnyou"

def test_literal_romaji():
    assert get_keystrokes("KA,nn", mode="romaji")[0] == "ka,nn"
    with pytest.raises(ValueError):
        get_keystrokes("かな", mode="romaji")

def test_center():
    rows = load_layout(LAYOUT)
    s = calculate("bbbjjjggmmvvk", rows)
    assert s["center_total"] == 13
    assert s["center_keys"] == ["b", "g", "j", "k", "m", "v"]

def test_report_generation(tmp_path):
    input_file = tmp_path / "kana.txt"
    input_file.write_text("かなです。", encoding="utf-8")
    result = generate_heatmap(input_file, LAYOUT, tmp_path / "report", mode="kana")
    assert result["estimated_keypresses"] == len("kanadesu.")
    assert (tmp_path / "report" / "heatmap.html").is_file()
    assert (tmp_path / "report" / "key_counts.csv").is_file()
    assert (tmp_path / "report" / "summary.json").is_file()
    assert json.loads((tmp_path / "report" / "summary.json").read_text())["typing_model"] == "estimate; not observed typing"
    with (tmp_path / "report" / "key_counts.csv").open(encoding="utf-8-sig") as f:
        assert any(row["key"] == "a" and row["count"] == "2" for row in csv.DictReader(f))

def test_empty_rejected(tmp_path):
    file = tmp_path / "empty.txt"
    file.write_text(" \n", encoding="utf-8")
    with pytest.raises(ValueError):
        generate_heatmap(file, LAYOUT, tmp_path / "out")
