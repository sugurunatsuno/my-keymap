#!/usr/bin/env python3
"""Merge EffiveRoman suffix entries into an exported Google Japanese Input romaji table.

The IME import replaces the entire table. Merge the user's actual exported
table instead of importing a suffix-only file.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_base(path: Path) -> list[list[str]]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        columns = line.split("\t")
        if len(columns) not in (2, 3) or not columns[0] or not columns[1]:
            raise ValueError(f"{path}:{number}: 2〜3列のローマ字テーブルではありません")
        rows.append(columns)
    if not rows:
        raise ValueError("空のローマ字テーブルです")
    return rows


def read_suffixes(path: Path, trial_only: bool) -> list[list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if not {"入力", "かな", "扱い"}.issubset(reader.fieldnames or []):
            raise ValueError("単語帳の列が不足しています")
        result = []
        for entry in reader:
            if trial_only and entry["扱い"] != "初期試用":
                continue
            result.append([entry["入力"], entry["かな"]])
    return result


def merge(base: list[list[str]], suffixes: list[list[str]]) -> tuple[list[list[str]], int]:
    rules: dict[str, list[str]] = {}
    ordered: list[list[str]] = []
    for row in base:
        old = rules.get(row[0])
        if old is not None:
            if old != row:
                raise ValueError(f"入力 {row[0]!r} に重複した異なる規則があります")
            continue
        rules[row[0]] = row
        ordered.append(row)
    added = 0
    for code, kana in suffixes:
        old = rules.get(code)
        if old is not None:
            if old[1] == kana and (len(old) == 2 or not old[2]):
                continue
            raise ValueError(f"入力 {code!r} は既存規則 {old!r} と競合します")
        longer = [existing for existing in rules if existing.startswith(code)]
        if longer:
            raise ValueError(f"入力 {code!r} は既存の長い規則 {longer[:5]!r} の接頭辞です")
        shorter = [existing for existing in rules if code.startswith(existing)]
        if shorter:
            raise ValueError(f"入力 {code!r} は既存の短い規則 {shorter[:5]!r} を含みます")
        row = [code, kana]
        rules[code] = row
        ordered.append(row)
        added += 1
    return ordered, added


def main() -> None:
    parser = argparse.ArgumentParser(description="Google日本語入力のローマ字テーブルへ語尾拡張を統合")
    parser.add_argument("base", type=Path, help="Google日本語入力からエクスポートした元テーブル")
    parser.add_argument("output", type=Path, help="統合後のGoogle日本語入力インポート用ファイル")
    parser.add_argument("--lexicon", type=Path, default=Path("lexicons/effiveroman-suffixes.tsv"))
    parser.add_argument("--trial-only", action="store_true", help="初期試用8件だけ追加")
    args = parser.parse_args()
    if args.base.resolve() == args.output.resolve():
        parser.error("元のエクスポートファイルと出力先を分けてください")
    try:
        rows, count = merge(read_base(args.base), read_suffixes(args.lexicon, args.trial_only))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("\n".join("\t".join(row) for row in rows) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"追加規則: {count}件 / 合計: {len(rows)}件 -> {args.output}")
    print("元テーブルは変更していません。インポート前に内容を確認してください。")


if __name__ == "__main__":
    main()
