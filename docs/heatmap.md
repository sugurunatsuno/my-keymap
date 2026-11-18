# 日本語テキストからキー使用頻度を可視化する

65% Colemak派生配列で、テキストから推定したキーの入力回数をヒートマップで表示するためのローカル実験です。カメラは不要です。

## 初回の動作確認

リポジトリ直下で実行します。

```bash
python -m pip install -e .
python -m keylab heatmap samples/mini_kana.txt
```

`reports/heatmap/heatmap.html` をブラウザで開くと配列上に頻度が表示されます。
`key_counts.csv` はキー別頻度、`summary.json` は集計条件と中央キーの頻度です。

## 自分の文章で試す

UTF-8の `corpus.txt` をリポジトリ直下に用意して実行します。

```bash
# 漢字を含む文章を変換するための辞書を追加
python -m pip install -e '.[japanese]'
python -m keylab heatmap corpus.txt --out-dir reports/my-corpus
```

かなだけの文章は追加ライブラリ不要です。すでにローマ字の打鍵列になっている場合は
`python -m keylab heatmap corpus.txt --mode romaji` を指定してください。

## 変換規則と注意点

- 標準では `し=si`、`ち=ti`、`つ=tu`、`ふ=hu`、`じ=zi`、`ん=nn`、`っか=kka` など、IME入力を近似した綴りです。
- `--n-style contextual` を指定すると、一部の子音の前で `ん=n` として比較できます。
- 漢字の読みはpykakasiによる辞書推定なので、固有名詞や多義語は誤る場合があります。読みの精度を揃えるなら、ひらがなで読みに直した文章を使ってください。
- 省略入力、Shift、IME変換の確定、候補選択、キーの押し直し、レイヤー操作は計算に入れていません。
- キーの色は頻度を示すもので、押しやすさや運指の移動距離ではありません。
- サンプルはテスト用の短文で、日本語全体の頻度を代表しません。
- レポートと `corpus.txt` はGitの追跡対象から外しています。生の文章をGitHubに投稿しないでください。
