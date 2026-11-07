# CLAUDE.md — Mind_Navi 開発ルール

このリポジトリで作業する Claude は、最初にこのファイルを読むこと。仕様の詳細は `docs/SPEC.md`（正本）にある。

## 利用者
- 呼称は「Dr. Ishida」。やり取りは日本語。
- GitHub に不慣れ。操作の説明は具体的に、専門用語は避ける。
- 推測で仕様や文書の内容を補わない。分からないことは聞く。

## 構成
| パス | 内容 |
|---|---|
| `desktop/mind_navi.py` | PC版本体（Python／tkinter、**1ファイル構成**、約2.1万行） |
| `android/MindNaviShopping/` | Android版 買い物リスト（Java、外部ライブラリなし） |
| `installer/` | Windows インストーラー（未着手） |
| `docs/SPEC.md` | 仕様・決定事項・経緯（正本） |
| `samples/mind_navi_sample.json` | 全項目入りのダミーデータ |
| `tests/` | 自動テスト（`python -m unittest discover tests`） |
| `CHANGELOG.md` | 変更履歴 |

## 作業のルール（必ず守る）
1. **方針の変更は先に確認する**。`docs/SPEC.md` の「4. UI・デザインのルール」「6. 決定事項」と異なる実装をする場合は、実装前に Dr. Ishida に確認する。
2. **mind_navi.py は全体を読まない**。巨大なため、`grep` で場所を探して必要な範囲だけ読み、Edit で部分的に直す。ファイル全文を出力・再生成しない。
3. **1ファイル構成を保つ**（モジュールに分けない）。必須は標準ライブラリのみ。追加ライブラリは任意機能だけで使い、無くても起動できるようにする。
4. ソース冒頭の「VERSION／最終更新日」と末尾の `# END OF FILE` を残す。最終更新日は変更のたびに更新する。版番号を上げるかどうかは Dr. Ishida に確認する。
5. 変更したら `CHANGELOG.md` に追記し、新しく決まったことは `docs/SPEC.md`（主に6章・必要なら5章）に書く。チャットではなくこのリポジトリを正本にする。
6. コミットは機能ごとに小さく、メッセージは日本語。
7. 変更後は `python -m unittest discover tests` を実行する。GUI を確認するときは tkinter と xvfb を使う（クラウド環境に tkinter が無ければ `apt-get install python3-tk`）。

## UI の絶対ルール（全画面共通）
- リストに追加するとき、別の入力欄（コンソール）を設けない。**リストに直接入力**する（いちばん下の「＋ 新しい◯◯」行など）。
- **入力中に文字を大きくしない**。入力欄は表示中の文字と同じ大きさ・書体でセルに重ねる。
- 4象限の色（カレンダー・タスクリスト・ガント共通）：Core＝赤 #e03131、Operational＝青 #1c7ed6、Strategic＝緑 #2f9e44、Divest＝灰 #868e96、Adhoc＝黄 #f5b800。コード内のキーは core/infra/ambition/bull（名前を変えない）。
- タスクの重要度・必要度・緊急度は6段階で **1が最も高い**（1〜3が高）。購入分析は逆で6が高い（統一するかは未確定）。
- 用語：「Adhoc」「タスクリスト」「買い物リスト」。

## データの互換（壊さない）
- データは1つの JSON ファイルにすべて入れる。同じフォルダに同内容の `<名前>.backup.json` を書く。
- 読んだ未知の属性は消さずに書き戻す。データ形式を変えるときは古いデータの読み替えを入れる。
- Android版は同じファイルの `view.groceries` だけを書き換える。**PC版の買い物リストの仕様を変えたら Android版も合わせ、`app/build.gradle` の versionCode を1つ上げる**。
- 個人の実データ（`*.json` のデータファイル）はリポジトリに入れない（`samples/` のダミーだけ）。

## Android版
- ラムダ式・メソッド参照を使わない（Gradle なしのビルドで動かなくなる。匿名クラスで書く）。
- ビルドは `android/MindNaviShopping/tools/build_apk.sh`（手順は `docs/SPEC.md` 11章）。
- **署名の鍵とパスワードはリポジトリに入れない**。署名付き APK が必要なときは、鍵の受け渡し方を Dr. Ishida に確認する（方法は未確定）。

## 名称（旧称 TaskMap）
- 2026-11-08 に TaskMap から Mind_Navi へ名前を変えた。新しく書くものはすべて Mind_Navi にする。
- 旧名のまま残すもの（変えると既存データと食い違う）：Google カレンダーの照合キー `taskmap_id`、ICS の UID `@taskmap`、旧版からの取り込み元 `~/.taskmap_shopping.json` など4つ、起動時に旧設定を引き継ぐ処理（`migrate_old_local_files`・`_migrate_data_dir`）、署名の鍵の別名 `taskmap`、互換用の別名 `TaskMap = MindNavi`。詳細は `docs/SPEC.md` 冒頭。

## 既知の課題
`docs/SPEC.md` の 9章（未確認事項・ヘルプとコードの食い違い）を参照。
