"""Estimate key-frequency changes after applying Japanese IME suffix expansions.

Results are hypothetical: they assume every available abbreviation is used, with
an optimal non-overlapping choice. They do not measure actual typing behavior.
"""

from __future__ import annotations

import csv
import html
import json
from collections import Counter
from pathlib import Path

from .heatmap import (
    DIGRAPHS, KANA, PUNCTUATION, add_kanji_readings, calculate,
    kana_to_romaji, load_layout, render_html, to_hiragana,
)


def read_lexicon(path: Path) -> list[dict[str, str]]:
    """Read the user-facing EffiveRoman TSV; reject duplicate or invalid codes."""
    with Path(path).open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        if not {"入力", "かな", "扱い"}.issubset(reader.fieldnames or []):
            raise ValueError("語尾拡張TSVには入力、かな、扱いの列が必要です")
        entries = []
        seen = set()
        for row in reader:
            code = row["入力"].strip().lower()
            kana = to_hiragana(row["かな"].strip())
            if not code.isascii() or not code.isalpha() or len(code) != 2:
                raise ValueError(f"2英字の入力ではありません: {code!r}")
            if not kana or code in seen:
                raise ValueError(f"空または重複した規則です: {code!r}")
            if not all("ぁ" <= char <= "ゖ" for char in kana):
                raise ValueError(f"かな以外の出力です: {kana!r}")
            entries.append({"input": code, "kana": kana, "trial": row["扱い"] == "初期試用"})
            seen.add(code)
    if not entries:
        raise ValueError("語尾拡張規則がありません")
    return entries


def _normal_parts(source: str, n_style: str, small_kana_style: str) -> list[str]:
    """Attach the normal IME-like roman spelling to each kana character.

    Empty parts represent the continuation of a contracted syllable, such as
    the second codepoint in しゃ. They must never become independent fragments.
    """
    parts = [""] * len(source)
    i = 0
    accumulated = []
    while i < len(source):
        char = source[i]
        if char == "ん":
            if n_style == "contextual" and i + 1 < len(source):
                next_kana = source[i + 1]
                next_romaji = DIGRAPHS.get(source[i + 1:i + 3]) or KANA.get(next_kana, "")
                roman = "nn" if not next_romaji or next_romaji[0] in "any" else "n"
            else:
                roman = "nn"
        elif char == "っ":
            next_romaji = DIGRAPHS.get(source[i + 1:i + 3]) or KANA.get(source[i + 1:i + 2], "")
            if next_romaji and next_romaji[0] not in "aeiouxy":
                roman = next_romaji[0]
            else:
                roman = small_kana_style + "tu"
        elif char == "ー":
            roman = next((c for c in reversed("".join(accumulated)) if c in "aeiou"), "")
        elif source[i:i + 2] in DIGRAPHS:
            roman = DIGRAPHS[source[i:i + 2]]
            parts[i] = roman
            accumulated.append(roman)
            i += 2
            continue
        elif char in KANA:
            roman = KANA[char]
            if char in "ぁぃぅぇぉゃゅょゎゕゖ":
                roman = small_kana_style + roman[1:]
        elif char in PUNCTUATION:
            roman = PUNCTUATION[char]
        elif "A" <= char <= "Z" or "a" <= char <= "z" or "0" <= char <= "9":
            roman = char.lower()
        elif char in "-=[]\\;',./`":
            roman = char
        else:
            roman = ""
        parts[i] = roman
        accumulated.append(roman)
        i += 1
    return parts


def transform(source: str, entries: list[dict[str, str]], mode: str,
              n_style: str = "double", small_kana_style: str = "l") -> dict:
    """Choose the minimum-keystroke segmentation under active suffix rules.

    Substitutions are non-overlapping. Ties prefer normal input, preventing
    meaningless use of snippets that save no keys. The original text is not
    altered and output represents hypothetical input, not observed strokes.
    """
    if mode not in ("none", "trial", "all"):
        raise ValueError("拡張モードは none / trial / all を指定してください")
    if n_style not in ("double", "contextual") or small_kana_style not in ("l", "x"):
        raise ValueError("n_styleまたはsmall_kana_styleが不正です")
    active = [x for x in entries if mode == "all" or (mode == "trial" and x["trial"])] if mode != "none" else []
    normalized = to_hiragana(source)
    parts = _normal_parts(normalized, n_style, small_kana_style)
    normal_keys = "".join(parts)
    length = len(normalized)
    # dp[i] is minimum number of user key presses from index i to the end.
    dp = [0] * (length + 1)
    choice: list[dict | None] = [None] * length
    for i in range(length - 1, -1, -1):
        best = len(parts[i]) + dp[i + 1]
        winning = None
        for rule in active:
            suffix = rule["kana"]
            j = i + len(suffix)
            if j > length or not normalized.startswith(suffix, i):
                continue
            # Do not split contracted kana or sokuon from their following kana.
            if (i > 0 and normalized[i - 1] == "っ") or (i > 0 and not parts[i]):
                continue
            if j < length and not parts[j]:
                continue
            if 2 + dp[j] < best:
                best = 2 + dp[j]
                winning = {"end": j, "input": rule["input"], "kana": suffix}
        dp[i] = best
        choice[i] = winning
    i = 0
    keystrokes = []
    usage = Counter()
    while i < length:
        selected = choice[i]
        if selected is not None:
            keystrokes.append(selected["input"])
            usage[selected["input"]] += 1
            i = selected["end"]
        else:
            keystrokes.append(parts[i])
            i += 1
    keys = "".join(keystrokes)
    return {
        "keys": keys,
        "normal_keys": normal_keys,
        "saved": len(normal_keys) - len(keys),
        "usage": dict(sorted(usage.items())),
        "active_rules": len(active),
    }


def compare_ime_heatmaps(input_path: Path, layout_path: Path, lexicon_path: Path,
                         out_dir: Path, n_style: str = "double",
                         small_kana_style: str = "l") -> dict:
    input_path, layout_path, lexicon_path, out_dir = map(
        Path, (input_path, layout_path, lexicon_path, out_dir)
    )
    text = input_path.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise ValueError("入力文章が空です")
    if any("\u3400" <= c <= "\u9fff" or "\uf900" <= c <= "\ufaff" for c in text):
        text = add_kanji_readings(text)
    layout = load_layout(layout_path)
    entries = read_lexicon(lexicon_path)
    results = {}
    out_dir.mkdir(parents=True, exist_ok=True)
    for mode in ("none", "trial", "all"):
        output = transform(text, entries, mode, n_style, small_kana_style)
        if not output["keys"]:
            raise ValueError("テキストからローマ字の入力列を生成できませんでした")
        stats = calculate(output["keys"], layout)
        mode_dir = out_dir / mode
        mode_dir.mkdir(exist_ok=True)
        html_report = render_html(layout, stats, input_path.name + " / " + mode,
                                  "kana + " + mode, n_style, small_kana_style)
        (mode_dir / "heatmap.html").write_text(html_report, encoding="utf-8")
        with (mode_dir / "key_counts.csv").open("w", encoding="utf-8-sig", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow(["key", "count", "share_percent"])
            for key, count in sorted(stats["counts"].items()):
                writer.writerow([key, count, round(count / stats["count"] * 100, 3)])
        results[mode] = {
            "estimated_keypresses": stats["count"],
            "saved_vs_none": output["saved"],
            "center_keypresses": stats["center_total"],
            "center_keys": stats["center_keys"],
            "used_rules": output["usage"],
            "active_rule_count": output["active_rules"],
            "counts": stats["counts"],
            "unplaced": stats["unplaced"],
        }
    if results["none"]["estimated_keypresses"] < results["trial"]["estimated_keypresses"] or results["trial"]["estimated_keypresses"] < results["all"]["estimated_keypresses"]:
        raise RuntimeError("省略入力を増やしたときの打鍵数が逆転しました")
    keys = sorted(set().union(*(r["counts"].keys() for r in results.values())))
    with (out_dir / "difference.csv").open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["key", "none", "trial8", "all35", "trial_delta", "all_delta"])
        for key in keys:
            a, b, c = (results[m]["counts"].get(key, 0) for m in ("none", "trial", "all"))
            writer.writerow([key, a, b, c, b - a, c - a])
    summarized = {
        "input_file": input_path.name,
        "layout": layout_path.name,
        "suffix_lexicon": lexicon_path.name,
        "n_style": n_style,
        "small_kana_style": small_kana_style,
        "method": "minimum keystrokes by nonoverlapping kana substring substitution",
        "caveat": "Idealized use of every applicable suffix; no typing observations; kana readings and IME behavior may differ.",
        "scenarios": results,
    }
    (out_dir / "comparison.json").write_text(json.dumps(summarized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "index.html").write_text(render_comparison(summarized), encoding="utf-8")
    return summarized


def render_comparison(summary: dict) -> str:
    s = summary["scenarios"]
    normal = s["none"]["estimated_keypresses"]
    rows = []
    for label, mode in [("通常入力", "none"), ("8件", "trial"), ("35件", "all")]:
        x = s[mode]
        n = x["estimated_keypresses"]
        pct = 100 * (normal - n) / normal if normal else 0
        used = ", ".join(f"{k}×{v}" for k, v in x["used_rules"].items()) or "なし"
        rows.append(f'<tr><td>{label}</td><td>{n}</td><td>{normal - n}</td><td>{pct:.1f}%</td><td>{x["center_keypresses"]}</td><td><a href="{mode}/heatmap.html">ヒートマップ</a></td><td>{html.escape(used)}</td></tr>')
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>IME語尾拡張のヒートマップ比較</title>
<style>body{{font:16px/1.6 system-ui,-apple-system,sans-serif;max-width:1000px;margin:30px auto;padding:0 16px;color:#263645}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ddd;padding:10px;text-align:left}}th{{background:#f1f5f8}}a{{color:#176f9a}}.note{{background:#f1f5f8;padding:16px;border-radius:10px}}@media(max-width:700px){{.table-wrap{{overflow:auto}}table{{min-width:750px}}}}</style></head><body>
<h1>IME語尾拡張の比較</h1><p>同じ文章: {html.escape(summary['input_file'])}<br>配列: {html.escape(summary['layout'])}<br>小書きかな: {html.escape(summary['small_kana_style'].upper())}</p>
<div class="table-wrap"><table><tr><th>モード</th><th>推定打鍵数</th><th>削減数</th><th>削減率</th><th>中央6キー</th><th>詳細</th><th>使用した短縮</th></tr>{''.join(rows)}</table></div>
<p><a href="difference.csv">キーごとの増減CSV</a> / <a href="comparison.json">集計JSON</a></p>
<div class="note">これは短縮規則を使える箇所では必ず使うと仮定した理論計算です。実測の打鍵、入力速度、指の移動、IMEの変換過程を計測したものではありません。漢字の読みは辞書推定であり、誤りがあり得ます。</div>
</body></html>'''