# Starsector 日本語化 (0.98a-RC8)

Starsector 0.98a-RC8 を日本語で遊ぶための非公式日本語化パッケージです。
データ層（CSV/JSON）・UI・会話/イベント文に加えて、本体コードに直書きされた
テキストまで、画面に見える文の約98〜99%を日本語化します
（抽出ユニット全体では約93%、残りはデバッグ文字列や内部キーなど非表示のものが大半）。

Unofficial Japanese localization for Starsector 0.98a-RC8. Covers data files,
UI, dialogue, and even text hardcoded in the game jars (applied locally by a
patcher — no game code is included in this package).

## 動作環境

- Starsector **0.98a-RC8**（他のバージョンではパッチャーが安全のため中止します）
- Windows（パッチャー自体は Python 3 があれば動きます）
- Python 3（パッチャー実行に必要。https://www.python.org/ から入手）
- 日本語フォント Mod（下記、別途導入が必要）

## 導入手順

### 1. 日本語フォント Mod を入れる

hirmiura 氏の [Japanese Fonts](https://github.com/hirmiura/starsector-mod-japanesefonts)
をダウンロードし、`Starsector/mods/` に入れてランチャーで有効化してください。
そのまま有効化できない場合は、フォント Mod の `mod_info.json` の
`gameVersion` を `0.98a-RC8` に書き換えてください。
（フォント Mod は本パッケージに含まれていません）

### 2. 本 Mod を入れる

`mod/StarsectorJP` フォルダを `Starsector/mods/` にコピーし、
ランチャーで「Starsector JP by game_loca_lab」を有効化してください。

### 3. パッチャーを実行する（コード層の日本語化）

`patcher` フォルダの中の `run_patcher.bat` を実行してください。
うまくいかない場合はコマンドプロンプトで:

```
python apply_patch.py "E:\Starsector"
```

（引数は Starsector のインストールフォルダ。省略時は自動検出します）

パッチャーが行うこと:

- `starsector-core/starfarer.api.jar` と `starfarer_obfuscated.jar` の
  表示文字列だけを日本語に書き換え（元ファイルは `.orig` として自動バックアップ）
- `starsector-core/data/strings/` の `tips.json` / `ship_names.json` を
  日本語版に差し替え（こちらも `.orig` バックアップあり）
- バージョンが一致しない jar は検出して何も変更しません

### 4. 起動して確認

タイトルメニューが日本語になっていれば導入成功です。

## 元に戻す

```
python apply_patch.py --restore "E:\Starsector"
```

で jar と本体ファイルが復元されます。Mod とフォント Mod は
ランチャーで無効化するか、フォルダごと削除してください。

## 既知の残り（仕様上・意図的に残しているもの）

- 一部の単語ラベル、人名プール、画像に焼き込まれた文字
- ポーズメニューの「Exit」「Ok」（内部 ID を兼ねている可能性があり、
  訳すとボタンが壊れる恐れがあるため意図的に保持）
- ゲーム内の一部 UI の「next」表示（メソッド名と格納場所を共有しており
  書き換えるとエラーになるため保持）

## 注意

- ゲームの公式アップデートが来ると、本体ファイルは上書きされ、
  パッチャーもバージョン不一致で中止するようになります。
  その場合は本パッケージの更新をお待ちください。
- セーブデータとの互換性は開発環境では確認済みですが、念のため
  導入前にセーブのバックアップを推奨します。

## クレジット・免責

- 翻訳・制作: ゲーム日本語化ラボ（[@game_loca_lab](https://x.com/game_loca_lab) / [note](https://note.com/game_loca_lab)）
- 日本語フォント: hirmiura 氏（別配布、上記リンク参照）
- Starsector © Fractal Softworks. 本パッケージは非公式のファンメイドです。
- 本パッケージにはゲーム本体の jar・コードは含まれていません。
  パッチャーは利用者自身のゲームファイルだけを書き換えます。
- 再配布・改変は、出典を明記のうえ非商用に限ります。
