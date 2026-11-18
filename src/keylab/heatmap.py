"""Local-only keyboard usage heatmaps from Japanese text and romaji input.

The map estimates keypresses under a documented IME-like romaji convention.
It is NOT a measurement of a person's actual typing or hand movements.
"""

from __future__ import annotations

import csv
import html
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Iterable

# Conservative keyboard-IME-style romaji, not a publication transliteration.
# Long vowels are entered as each kana (e.g. こう = kou), not as macrons.
_ROWS = [
    ("あいうえお", "a i u e o"),
    ("かきくけこ", "ka ki ku ke ko"),
    ("さしすせそ", "sa si su se so"),
    ("たちつてと", "ta ti tu te to"),
    ("なにぬねの", "na ni nu ne no"),
    ("はひふへほ", "ha hi hu he ho"),
    ("まみむめも", "ma mi mu me mo"),
    ("やゆよ", "ya yu yo"),
    ("らりるれろ", "ra ri ru re ro"),
    ("わゐゑを", "wa wi we wo"),
    ("がぎぐげご", "ga gi gu ge go"),
    ("ざじずぜぞ", "za zi zu ze zo"),
    ("だぢづでど", "da di du de do"),
    ("ばびぶべぼ", "ba bi bu be bo"),
    ("ぱぴぷぺぽ", "pa pi pu pe po"),
    ("ぁぃぅぇぉ", "xa xi xu xe xo"),
    ("ゃゅょ", "xya xyu xyo"),
]
KANA = {
    kana: roman
    for kanas, romans in _ROWS
    for kana, roman in zip(kanas, romans.split())
}
KANA.update({"ゔ": "vu", "ゎ": "xwa", "ゕ": "xka", "ゖ": "xke", "っ": "xtu", "ゑ": "we"})
DIGRAPHS = {}
for start, prefix in {
    "き": "ky", "ぎ": "gy", "し": "sy", "じ": "zy", "ち": "ty", "ぢ": "dy",
    "に": "ny", "ひ": "hy", "び": "by", "ぴ": "py", "み": "my", "り": "ry",
}.items():
    for small, vowel in zip("ゃゅょ", "auo"):
        DIGRAPHS[start + small] = prefix + vowel
# Additional loanword digraphs supported by many Japanese IMEs.
for base, prefix in {"ふ": "f", "ゔ": "v", "て": "th", "で": "dh", "と": "tw", "ど": "dw"}.items():
    for small, vowel in zip("ぁぃぅぇぉ", "aiueo"):
        DIGRAPHS[base + small] = prefix + vowel
for base, prefix in {"く": "kw", "ぐ": "gw"}.items():
    DIGRAPHS[base + "ぁ"] = prefix + "a"
DIGRAPHS.update({"うぃ": "wi", "うぇ": "we", "うぉ": "who", "しぇ": "sye", "じぇ": "zye", "ちぇ": "tye"})
# key mapping is a convenience approximation; symbols requiring Shift are not modeled.
PUNCTUATION = {"。": ".", "、": ",", "｡": ".", "､": ","}
KANJI_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
JAPANESE_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff]")


def to_hiragana(text: str) -> str:
    """NFKC-normalize text and fold katakana to hiragana, preserving ASCII."""
    text = unicodedata.normalize("NFKC", text)
    return "".join(chr(ord(c) - 0x60) if 0x30A1 <= ord(c) <= 0x30F6 else c for c in text)


def add_kanji_readings(text: str) -> str:
    """Resolve kanji to hiragana using optional pykakasi; fail clearly if absent."""
    if not KANJI_RE.search(text):
        return text
    try:
        import pykakasi
    except ImportError as exc:
        raise ValueError(
            "漢字を含むため読み変換が必要です。python -m pip install -e '.[japanese]' "
            "を実行するか、かな文/ローマ字文を入力してください。"
        ) from exc
    converter = pykakasi.kakasi()
    # Convert line by line to keep the input segmentation across paragraphs.
    return "".join(
        "".join(item.get("hira", item["orig"]) for item in converter.convert(line))
        for line in text.splitlines(keepends=True)
    )


def kana_to_romaji(text: str, n_style: str = "double") -> tuple[str, Counter[str]]:
    """Convert kana and literal ASCII keys to keyboard-like keystrokes.

    Returns (keystrokes, unconverted_character_counts). `nn` always unambiguous
    for ん. In contextual mode, single n is used before a following consonant.
    """
    if n_style not in {"double", "contextual"}:
        raise ValueError("n_style must be 'double' or 'contextual'")
    s = to_hiragana(text)
    out: list[str] = []
    skipped: Counter[str] = Counter()
    i = 0
    while i < len(s):
        char = s[i]
        following = s[i + 1 : i + 3]
        if char == "ん":
            # A single n before a vowel/y or at a boundary can be ambiguous.
            if n_style == "contextual" and i + 1 < len(s):
                next_char = s[i + 1]
                if next_char in KANA or next_char in {"っ", "ん"}:
                    next_pair = s[i + 1 : i + 3]
                    next_romaji = DIGRAPHS.get(next_pair) or KANA.get(next_char, "")
                    value = "nn" if not next_romaji or next_romaji[0] in "any" else "n"
                else:
                    value = "nn"
            else:
                value = "nn"
            out.append(value)
        elif char == "っ":
            next_pair = s[i + 1 : i + 3]
            next_romaji = DIGRAPHS.get(next_pair) or KANA.get(s[i + 1 : i + 2], "")
            if next_romaji and next_romaji[0] not in "aeiouxy":
                out.append(next_romaji[0])
            else:
                out.append("xtu")
        elif char == "ー":
            vowel = next((c for c in reversed("".join(out)) if c in "aeiou"), None)
            if vowel is None:
                skipped[char] += 1
            else:
                out.append(vowel)
        elif s[i : i + 2] in DIGRAPHS:
            out.append(DIGRAPHS[s[i : i + 2]])
            i += 1
        elif char in KANA:
            out.append(KANA[char])
        elif char in PUNCTUATION:
            out.append(PUNCTUATION[char])
        elif "A" <= char <= "Z" or "a" <= char <= "z" or "0" <= char <= "9":
            out.append(char.lower())
        elif char in "-=[]\\;',./`":
            out.append(char)
        elif char.isspace() or char in "「」『』（）()！？!?：:・…〜～、":
            pass  # Punctuation not modeled; do not assume a key or layer.
        else:
            skipped[char] += 1
        i += 1
    return "".join(out), skipped


def get_keystrokes(text: str, mode: str = "auto", n_style: str = "double") -> tuple[str, Counter[str]]:
    """Interpret text as kana/kanji (auto), kana only, or literal roman keystrokes."""
    if mode == "romaji":
        # Keep literal typed symbol events; ignore whitespace and non-key text.
        if JAPANESE_RE.search(text):
            raise ValueError("--mode romaji では日本語文字を扱えません。--mode auto を指定してください。")
        keys = "".join(c.lower() for c in text if ("a" <= c.lower() <= "z") or c.isascii() and (c.isdigit() or c in "-=[]\\;',./`"))
        return keys, Counter()
    if mode == "kana" and KANJI_RE.search(text):
        raise ValueError("--mode kana に漢字が含まれています。--mode auto を選択してください。")
    if mode not in {"auto", "kana"}:
        raise ValueError(f"Unknown input mode: {mode}")
    return kana_to_romaji(add_kanji_readings(text) if mode == "auto" else text, n_style=n_style)


def load_layout(path: Path) -> list[list[str]]:
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = obj.get("rows", [])
    if not rows:
        raise ValueError("Layout requires a nonempty rows array")
    keys = [r["keys"] for r in rows]
    if not all(isinstance(row, list) and all(isinstance(k, str) and k for k in row) for row in keys):
        raise ValueError("Layout rows must have nonempty keys")
    return keys


def calculate(keypresses: str, layout: list[list[str]]) -> dict:
    counts = Counter(keypresses.lower())
    known = {key.lower() for row in layout for key in row if len(key) == 1}
    unplaced = {key: count for key, count in counts.items() if key not in known}
    placed = {key: counts[key] for key in known}
    center = set()
    for row in layout[1:4]:
        # Letter rows: 1st row begins with Tab; 2nd with backtick; 3rd with Shift.
        # Deliberately only letters around the midpoint of the alphabet run.
        letters = [k.lower() for k in row if len(k) == 1 and k.isalpha()]
        center.update(letters[4:6])
    return {
        "count": sum(counts.values()),
        "placed_total": sum(placed.values()),
        "counts": dict(sorted(placed.items())),
        "unplaced": dict(sorted(unplaced.items())),
        "center_keys": sorted(center),
        "center_total": sum(counts[k] for k in center),
    }


def _color(value: int, maximum: int) -> str:
    if not value or not maximum:
        return "#e8edf1"
    fraction = (value / maximum) ** 0.5
    # Light orange -> deeper brick; higher count = darker and warmer.
    light = 93 - int(53 * fraction)
    return f"hsl(18 82% {light}%)"


def _key_width(key: str) -> int:
    return {"Space": 6, "Shift": 2, "Enter": 2, "Tab": 2, "Ctrl": 2,
            "Alt": 2, "Win": 2, "PgUp": 2, "PgDn": 2, "Home": 2,
            "Del": 2, "Esc": 2, "⌫": 2}.get(key, 1)


def render_html(layout: list[list[str]], stats: dict, source_name: str, mode: str, n_style: str) -> str:
    maximum = max(stats["counts"].values(), default=0)
    total = stats["count"]
    key_rows = []
    for row in layout:
        elements = []
        for key in row:
            n = stats["counts"].get(key.lower(), 0) if len(key) == 1 else 0
            percent = (100 * n / total) if total else 0
            bg = _color(n, maximum)
            foreground = "#fff" if n and n / maximum >= 0.55 else "#23303b"
            # Styling is approximate, not a geometry calibration.
            elements.append(
                f'<div class="key" style="--w:{_key_width(key)};background:{bg};color:{foreground}" '
                f'title="{html.escape(key, quote=True)}: {n:,} ({percent:.2f}%)">'
                f'<span class="letter">{html.escape(key)}</span>'
                f'<span class="detail">{n:,}</span></div>'
            )
        key_rows.append('<div class="key-row">' + "".join(elements) + '</div>')
    top = sorted(((k, v) for k, v in stats["counts"].items() if v), key=lambda item: (-item[1], item[0]))[:15]
    lines = "".join(f'<tr><td>{html.escape(k.upper())}</td><td>{v:,}</td><td>{100*v/total:.2f}%</td></tr>' for k, v in top) if total else ""
    unplaced = ", ".join(f"{k}: {v}" for k, v in stats["unplaced"].items()) or "なし"
    center_keys = ", ".join(k.upper() for k in stats["center_keys"])
    pct = (stats["center_total"] / total * 100) if total else 0
    return f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Keyboard Layout Lab | Heatmap</title>
<style>
:root{{font-family:system-ui,-apple-system,"Noto Sans JP",sans-serif;color:#22313c;background:#f5f7fa}}
body{{max-width:1250px;margin:0 auto;padding:28px 18px}}h1{{margin:0 0 8px}}p{{line-height:1.6}}
header,.panel{{padding:22px;background:white;border:1px solid #e1e6ea;border-radius:14px;margin-bottom:16px}}
.summary{{display:flex;gap:12px;flex-wrap:wrap}}.stat{{padding:10px 16px;background:#f1f5f8;border-radius:10px}}
.stat strong{{display:block;font-size:1.5rem}}.keyboard{{overflow-x:auto;padding:15px 0}}
.key-row{{display:flex;gap:5px;justify-content:center;margin:5px auto;min-width:780px}}
.key{{height:64px;flex:var(--w) 1 0;min-width:0;border:1px solid #bbc8d1;border-radius:7px;
 display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:0 2px 0 #c7d0d8}}
.letter{{font-weight:700;font-size:.95rem}}.detail{{font-size:.75rem;opacity:.85;font-variant-numeric:tabular-nums}}
.caption{{font-size:.85rem;color:#566570}}table{{border-collapse:collapse;width:100%;max-width:450px}}
th,td{{padding:7px 10px;text-align:left;border-bottom:1px solid #edf0f3}}th{{background:#f1f5f8}}
@media(max-width:680px){{body{{padding:12px}}.panel{{padding:14px}}.key-row{{min-width:750px}}}}
</style></head><body>
<header><h1>Keyboard Layout Lab / キー使用頻度</h1>
<p>入力: <code>{html.escape(source_name)}</code> ｜ モード: {html.escape(mode)} ｜ ん: {html.escape(n_style)}</p>
<div class="summary"><div class="stat">推定打鍵数<strong>{total:,}</strong></div>
<div class="stat">配置内の打鍵<strong>{stats['placed_total']:,}</strong></div>
<div class="stat">中央の文字キー ({html.escape(center_keys)})<strong>{stats['center_total']:,} / {pct:.1f}%</strong></div></div></header>
<section class="panel"><h2>配列上のヒートマップ</h2><p>濃い色ほど出現回数が多くなります。数字は推定打鍵回数です。</p>
<div class="keyboard">{''.join(key_rows)}</div>
<p class="caption">表示位置とキー幅は概略です。US/JISの物理的な形状を表現したものではありません。</p></section>
<section class="panel"><h2>頻出キー 上位15件</h2><table><thead><tr><th>キー</th><th>回数</th><th>割合</th></tr></thead><tbody>{lines}</tbody></table>
<p>配列外キー: {html.escape(unplaced)}</p>
<p class="caption">かな・漢字から推定したローマ字列の頻度であり、実測キー入力ログではありません。IMEの綴り方、変換時の操作、候補選択、修正操作、Shiftやレイヤー入力は考慮していません。漢字の読みは辞書推定で誤りがあり得ます。</p></section>
</body></html>'''


def generate_heatmap(input_path: Path, layout_path: Path, out_dir: Path,
                     mode: str = "auto", n_style: str = "double") -> dict:
    input_path = Path(input_path)
    layout_path = Path(layout_path)
    out_dir = Path(out_dir)
    source = input_path.read_text(encoding="utf-8-sig")
    layout = load_layout(layout_path)
    keystrokes, skipped = get_keystrokes(source, mode, n_style)
    if not keystrokes:
        raise ValueError("入力からローマ字キーを生成できません。文字の種類と --mode を確認してください。")
    stats = calculate(keystrokes, layout)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "heatmap.html").write_text(
        render_html(layout, stats, input_path.name, mode, n_style), encoding="utf-8"
    )
    with (out_dir / "key_counts.csv").open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["key", "count", "share_percent"])
        for key, count in sorted(stats["counts"].items(), key=lambda item: (-item[1], item[0])):
            writer.writerow([key, count, round(100 * count / stats["count"], 3)])
    summary = {
        "input_file": input_path.name, "layout_file": layout_path.name,
        "input_mode": mode, "n_style": n_style, "typing_model": "estimate; not observed typing",
        "estimated_keypresses": stats["count"], "placed_keypresses": stats["placed_total"],
        "center_keys": stats["center_keys"], "center_keypresses": stats["center_total"],
        "unplaced_keypresses": stats["unplaced"],
        "unconverted_characters": dict(skipped),
        "warnings": [
            "No typing observations were collected.",
            "IME conversion, candidates, edits, shift, layers, abbreviations and user-specific spelling not modeled.",
            "Input kanji readings may be incorrect; supplied corpus and conventions affect every result.",
        ],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary