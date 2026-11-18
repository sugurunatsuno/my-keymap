# IME語尾拡張あり/なしの比較ヒートマップ

U/Eを交換した65% Colemak派生配列で、同じ日本語文章から次の3通りの推定入力列を作ります。

- none: 通常ローマ字入力
- trial: 語尾拡張の初期試用8件を利用
- all: EffiveRoman式の語尾拡張35件を利用

## 実行

リポジトリ直下で、初回だけ `python -m pip install -e .` を実行してください。

```bash
python -m keylab heatmap-compare samples/mini_kana.txt
```

`reports/ime-compare/index.html` をブラウザで開きます。各条件のヒートマップと、キーごとの増減を確認できます。

35件のルールも効果が出るか確認したい場合は、動作確認用の例文で実行します。

```bash
python -m keylab heatmap-compare samples/ime_suffix_demo_kana.txt --out-dir reports/ime-demo
```

自分の文章を使う場合、リポジトリ直下にUTF-8の `corpus.txt` を用意してください。

```bash
# 漢字入り文章の読み推定が必要な場合は先に実行
python -m pip install -e '.[japanese]'
python -m keylab heatmap-compare corpus.txt --out-dir reports/my-ime
```

`corpus.txt` と `reports/` はGitの追跡対象外です。プライベートな文章をGitHubに送らずに集計できます。

配列ファイルの指定:

```bash
python -m keylab heatmap-compare corpus.txt --layout layouts/personal-colemak-derived-65.json --out-dir reports/original
python -m keylab heatmap-compare corpus.txt --layout layouts/personal-colemak-derived-65-ue-swap-v2.json --out-dir reports/ue
```

小書きかなの独立入力はデフォルトでL方式、`ん`は `nn` と見積もります。

## 動作確認用の結果

| 入力文章 | none | trial | all |
|---|---:|---:|---:|
| `mini_kana.txt` | 170 | 162 | 162 |
| `ime_suffix_demo_kana.txt` | 323 | 277 | 263 |

`mini_kana.txt` は `ms -> ます` を4回適用しました。AとUがそれぞれ4打鍵減りました。中央6キー B/J/G/M/V/K の推定打鍵回数は20回で変化しませんでした。

`ime_suffix_demo_kana.txt` は語尾拡張の動作確認のために作った短文です。特定の語尾を意図的に含めており、日本語の出現頻度を代表しません。

## 出力

- `index.html`: 3条件の比較表
- `none/heatmap.html`, `trial/heatmap.html`, `all/heatmap.html`: 各条件のキー頻度
- `difference.csv`: キー別の打鍵数差
- `comparison.json`: 条件、スニペット適用回数、推定打鍵数など

## 評価モデルの限界

- コーパス中の使える語尾拡張は、入力者がすべて使うものと仮定しています。
- 重なる語尾については、1つのかな文字を二重に短縮しないように入力回数が最小となる分割を採用します。
- Google日本語入力での実際のキーイベント、文脈依存の入力挙動、漢字変換、候補選択、誤打や学習負荷は未計測です。
- `っ` の直後で拡張語尾を割り込ませるなど、IMEの挙動が不確実な候補は安全側に除外しています。
- 漢字の読みは辞書推定です。読みを厳密に揃えるには、ひらがな主体のコーパスで試してください。
- ヒートマップの色はキーの出現頻度であり、押しやすさや手の移動距離ではありません。

今後はキー間遷移の距離指標を加え、入力者がスニペットを使用する割合も測定して再推定する予定です。
