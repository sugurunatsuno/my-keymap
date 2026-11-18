# Google日本語入力用 EffiveRoman 語尾拡張

このディレクトリには、Google日本語入力の「ローマ字テーブル」へインポートできる完成済みのテーブルを置きます。単語登録辞書用ではありません。

## インポートするファイル

- [35件の完全版](../ime/google-japanese-input-effive-suffixes-35.txt): 標準に近いローマ字規則311件 + 語尾拡張35件 = 346件
- [初期試用8件版](../ime/google-japanese-input-effive-suffixes-trial-8.txt): 標準に近いローマ字規則311件 + 語尾拡張8件 = 319件

行は「入力<TAB>出力[<TAB>次の入力]」です。コメントや見出しはありません。UTF-8で保存しています。基本ローマ字テーブルには `la`, `lyu`, `ltu` 等が含まれるため、Lによる小書きかな入力も維持できます。

## Google日本語入力に設定する

- Google日本語入力の「プロパティ」を開く
- 「一般」→「ローマ字テーブル」→「編集」を開く
- 編集画面のメニューから「エクスポート」を選び、現在のテーブルを別名でバックアップする
- 「インポート」から上記の `.txt` を選択する
- 上書き確認を読み、設定を適用する
- メモ帳などで `ds`→「です」、`dn`→「でした」、`ms`→「ます」、`mn`→「ました」、`la`→「ぁ」を確認する。通常の `konnnitiha` や `sya` も確認する

重要: インポートは現在のローマ字テーブル全体を上書きします。すでに独自のローマ字規則を設定している場合、上記の完成版を直接インポートしないでください。

## 既存のテーブルを残して語尾拡張だけ追加する

現在使用中のローマ字テーブルをエクスポートして `romantable-backup.txt` という名前で保存したとします。

```bash
python tools/merge_google_ime_table.py romantable-backup.txt ime/local/romantable-effive.txt
```

初期試用8件だけ追加する場合:

```bash
python tools/merge_google_ime_table.py romantable-backup.txt ime/local/romantable-trial.txt --trial-only
```

生成したファイルをインポートします。既存規則と入力コードが競合する場合、変換を行わずエラーを表示します。
元のエクスポートファイルは書き換えません。個人用の `ime/local/` 以下はGitの管理対象外です。

## 注意

- 元の35件は[EffiveRoman語尾拡張の資料](https://3kyoson.hatenablog.com/entry/effive/2)から整理した候補です。元のEffiveRomanに含まれるその他の拡張は含みません。
- 完成版の基礎ローマ字規則には [tomoemon/google_input](https://github.com/tomoemon/google_input) で公開されたGoogle日本語入力の既定値の再現データを利用しています（Apache-2.0、[ライセンス](../third_party/tomoemon-google-input-LICENSE)）。お使いのGoogle日本語入力自身からエクスポートした完全なテーブルではありません。
- 同じ入力文字列との完全一致の衝突と、追加コードが既存規則の接頭辞になるケースは確認しました。変換途中のIME固有の動作やすべての文章での互換性は実機未検証です。
- Google日本語入力でのローマ字テーブル変更は、OSの物理キー配列やU/Eの位置を変更しません。文字キー配置の変更は別途行う必要があります。
