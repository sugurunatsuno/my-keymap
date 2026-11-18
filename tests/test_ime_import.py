from pathlib import Path
import importlib.util

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("merge_ime_table", ROOT / "tools" / "merge_google_ime_table.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_import_tables_are_full_and_unique():
    for filename, expected in [
        ("google-japanese-input-effive-suffixes-35.txt", 346),
        ("google-japanese-input-effive-suffixes-trial-8.txt", 319),
    ]:
        lines = (ROOT / "ime" / filename).read_text(encoding="utf-8").splitlines()
        rules = [line.split("\t") for line in lines]
        assert len(rules) == expected
        assert all(2 <= len(row) <= 3 for row in rules)
        assert len({row[0] for row in rules}) == expected
        assert {row[0]: row[1] for row in rules}["la"] == "ぁ"
        assert {row[0]: row[1] for row in rules}["ds"] == "です"
        assert {row[0]: row[1] for row in rules}["mn"] == "ました"


def test_merge_preserves_base_and_adds_suffixes():
    base = [["ka", "か"], ["la", "ぁ"], ["kk", "っ", "k"]]
    merged, added = module.merge(base, [["ds", "です"], ["mn", "ました"]])
    assert added == 2
    assert merged[:3] == base
    assert merged[-2:] == [["ds", "です"], ["mn", "ました"]]


def test_merge_rejects_conflicts():
    import pytest
    with pytest.raises(ValueError, match="競合"):
        module.merge([["ds", "違う"]], [["ds", "です"]])
    with pytest.raises(ValueError, match="接頭辞"):
        module.merge([["dsx", "たとえば"]], [["ds", "です"]])
