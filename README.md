# Keyboard Layout Lab

自分の手に合う日本語ローマ字入力向けキーボード配列を、実測と探索で研究するためのリポジトリです。

## 研究の出発点

- Colemak の運指は好感触だった。
- Eucalyn は指の動きと、中央付近の記号配置に違和感があった。
- 初期の対象は日本語ローマ字入力。将来的に AZIK に似た省略規則も評価する。
- 速さだけでなく、同指連続打鍵、指先の移動、エラー、習得コストを区別して測る。
- 計測から結論を出す前に、撮影条件・サンプル・誤差を保存する。

現在の実装は **カメラで両手の21点のランドマークを時刻付きで取得し、指先の移動量を集計する試作** です。押されたキー、打鍵速度、疲労度、配列の良し悪しを映像から自動判定するものではありません。

## 基準配列

今後の配列研究では、[ユーザー指定の65% Colemak派生配列](layouts/personal-colemak-derived-65.md) を設計上の基準とします。標準Colemakと同じものではありません。[JSON定義](layouts/personal-colemak-derived-65.json) も保存済みです。

日本語ローマ字入力を対象に、まず文字配置を固定した省略入力を検討します。その後、押しにくい中央キーの活用やレイヤーへの移動を評価します。現時点でOS/ファームウェアへの適用設定はありません。

## U/Eの交換候補

オリジナルの設計基準は保持したまま、Uをホーム段、Eを上段へ交換する[候補配列](layouts/personal-colemak-derived-65-ue-swap-v2.json)を追加しました。小書きかな入力のL方式もヒートマップで選択できます。比較方法は [docs/heatmap.md](docs/heatmap.md) を参照。

## IME語尾拡張を考慮したヒートマップ

通常入力 / 語尾拡張8件 / 語尾拡張35件を、同じ日本語テキストから比較できます。U/E交換後の配列、小書きかなL方式を既定値にしています。

```bash
python -m keylab heatmap-compare samples/mini_kana.txt
```

`reports/ime-compare/index.html` を開いて確認してください。自分の文章や、U/E交換前の配列でも比較できます。[比較手順](docs/ime-heatmap-compare.md)を参照。理論上の推定であり、実測した打鍵ログではありません。

## IME語尾拡張を前提とした配列評価

です/ますなどの短縮入力を実際に打ちやすいと感じているため、[IME拡張込みの評価方針](docs/ime-aware-layout.md)を採用します。今後は通常ローマ字列だけでなく、`ds` や `ms` などの短縮後のキー遷移も解析します。解析器と配列の再最適化はまだ未実装です。

## Google日本語入力への語尾拡張のインポート

[35件の完全版](ime/google-japanese-input-effive-suffixes-35.txt)と[初期試用8件版](ime/google-japanese-input-effive-suffixes-trial-8.txt)を作成しました。いずれもローマ字テーブルのインポート用ファイルで、単語登録辞書ではありません。

インポートすると現在のローマ字テーブルが上書きされます。先に必ず現在の設定をエクスポートして保存してください。独自設定がある場合は[統合ツール](tools/merge_google_ime_table.py)を使い、元の規則と語尾拡張を合わせたファイルを生成してください。

詳しくは[インポート手順](docs/google-ime-import.md)を参照。IME上での実動作は未検証です。

## EffiveRoman語尾拡張の単語帳

EffiveRomanの語尾拡張35件を[単語帳TSV](lexicons/effiveroman-suffixes.tsv)と[解説](docs/effiveroman-suffixes.md)に保存しました。最初の試用候補は8件ですが、現時点では実験前です。TSVは候補管理用であり、Google日本語入力へ直接インポートするものではありません。

## スニペットレイヤーの設計

通常のローマ字入力を残しながら、頻出するかな2文字/3文字を追加レイヤーで短縮入力する研究を進めます。U/E交換案と小書きかなのL入力を前提にした、[検討ノート](docs/snippet-layer.md)を作成しました。まだ実機向けのキーマップやマクロは実装していません。

## 日本語入力ヒートマップ

65% Colemak派生配列のキー使用頻度を日本語テキストから推定し、ブラウザで表示できます。カメラは不要です。

```bash
python -m pip install -e .
python -m keylab heatmap samples/mini_kana.txt
```

生成された `reports/heatmap/heatmap.html` をブラウザで開きます。自分のUTF-8の文章を使う場合は `python -m keylab heatmap corpus.txt` です。漢字を含むときは、先に `python -m pip install -e '.[japanese]'` を実行してください。

詳しくは [docs/heatmap.md](docs/heatmap.md) を参照。推定打鍵であり、実際の指の動きやキーイベントの記録ではありません。

## 最初に動かす

Python 3.10 以降を推奨。カメラが使える PC で実行します。

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
python -m pip install -e '.[camera]'
python -m keylab download-model
python -m keylab capture --duration 60 --layout colemak --task-id trial-01
python -m keylab analyze --latest
```

- `capture` の終了は `q`（プレビュー時）か Ctrl+C。 `--duration` 秒で自動終了。
- `--camera 1` で別のカメラを選択可能。 `--layout` / `--task-id` を指定すると比較時に区別できます。
- 映像そのものを保存したい場合だけ `--save-video` を追加。
- `landmarks.csv.gz` は時刻と21点の座標です。 `summary.csv` は指先と手首の移動量、手首に対する指先の相対移動量の集計です。
- `--preview` は画面を表示しますが、 `--save-video` を付けない限り動画は保存しません。

モデルは Google MediaPipe の Hand Landmarker を明示的な操作でダウンロードします。初回起動時に隠れてネットワークへ接続することはありません。

公式ドキュメント: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker

## 研究の進め方

最初は同じキーボード/カメラ位置/課題文で QWERTY、Colemak、Eucalyn を比較する設計を考えます。配列を実際に覚え直す効果は大きいので、習熟度が違う状態での単純比較は避けます。最初は自分の自然な入力時の手の動きを記録し、計測パイプラインを検証します。

測定指標は `docs/experiment.md`、カメラ映像の取り扱いは `docs/privacy.md` を参照。

## 使えるコマンド

```bash
python -m keylab --help
python -m keylab download-model --output models/hand_landmarker.task
python -m keylab capture --camera 0 --duration 120 --layout qwerty --task-id baseline-01
python -m keylab analyze --latest
python -m pytest -q
```

## 制約

- 動きの単位は画面上のピクセルです。カメラ位置や解像度が違う測定をそのまま比較しません。
- 追跡の途切れ、手の重なり、左右判定の変化は誤差になります。
- カメラだけではキー押下・配列ごとの正確な打鍵数・疲労は測れません。
- 生動画・キー入力の内容を GitHub にアップロードしないでください。 `.gitignore` に計測データとモデルを登録しています。
