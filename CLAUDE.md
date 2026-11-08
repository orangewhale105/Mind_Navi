# CLAUDE.md — Mind_Navi 開発ルール

このリポジトリで作業する Claude は、最初にこのファイルを読むこと。仕様の詳細は `docs/SPEC.md`（正本）にある。

## 利用者
- 呼称は「Dr. Ishida」。やり取りは日本語。
- GitHub に不慣れ。操作の説明は具体的に、専門用語は避ける。
- 推測で仕様や文書の内容を補わない。分からないことは聞く。
- **作業の終わりの報告には、毎回「取り込み〜ダウンロード〜入れ替え」の手順まで書く**（2026-11-08 Dr. Ishida の指示）。書く内容は下の「報告に必ず付ける手順」。

## 報告に必ず付ける手順（毎回そのまま書く。PR の番号・リンク、版番号、APK のファイル名は今回のものに）
1. **取り込み**：プルリクエストのリンクを開き、緑の「Merge pull request」→「Confirm merge」。紫の「Merged」が出れば完了。
2. **配布ファイルができるのを待つ**：取り込むと自動で作り始める（2026-11-08 から。PC版・Android版のプログラムが変わったときだけ）。https://github.com/orangewhale105/Mind_Navi →「Actions」で、いちばん上の「配布ファイルを作る」の黄色い丸が緑のチェックになれば完成（3〜5分）。赤い × なら「エラーが出た」と Claude に伝える。プログラムが変わらない取り込み（文書だけなど）では作られないので、その回は「ダウンロードし直す必要はありません」と書く。
3. **ダウンロード**：リポジトリのトップページ右側の「Releases」→ いちばん上（Latest）の「Assets」から、PC版 `mind_navi.py` と Android版 `MindNaviShopping_v◯.apk` を押す。スマホはブラウザで同じページを開いて APK を押す。
4. **入れ替え**：PC版はダウンロードした `mind_navi.py` を今のものと置き換えて起動（データファイルはそのまま使える）。Android版は APK を開いてインストール（上書きできる）。Android版を変えていないときは「Android版は変更なし（入れ直し不要）」と書く。

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
4. ソース冒頭の「VERSION／最終更新日」と末尾の `# END OF FILE` を残す。最終更新日は変更のたびに更新する。**版番号は指示（依頼）ごとに上げてよい**（PC版は 3.7 → 3.8 のように小数点以下を1つ。Android版は変えたときだけ versionName と versionCode を上げる。2026-11-08 Dr. Ishida の了承）。
5. 変更したら `CHANGELOG.md` に追記し、新しく決まったことは `docs/SPEC.md`（主に6章・必要なら5章）に書く。チャットではなくこのリポジトリを正本にする。
6. コミットは機能ごとに小さく、メッセージは日本語。作業が終わったら、**確認なしで main への取り込みの依頼（プルリクエスト）を作ってよい**（2026-11-08 Dr. Ishida の了承。取り込み〔Merge〕は Dr. Ishida が行う）。
7. 変更後は `python -m unittest discover tests` を実行する。GUI を確認するときは tkinter と xvfb を使う（クラウド環境に tkinter が無ければ `apt-get install python3-tk`）。

## UI の絶対ルール（全画面共通）
- リストに追加するとき、別の入力欄（コンソール）を設けない。**リストに直接入力**する（いちばん下の「＋ 新しい◯◯」行など）。
- **リストの操作はエクセルと同じ**（IN/OUT_Navi・買い物リスト PC/Android・タスクリスト）：入力しても並べ替えない（「⇅ 並べ替える」ボタンで）、セルを選んで矢印・Tab・Enter で移動、文字を打つと入力。仕組みは `GridNav`。新しいリストもこの操作にする。
- **入力中に文字を大きくしない**。入力欄は表示中の文字と同じ大きさ・書体でセルに重ねる。
- 4象限の色（カレンダー・タスクリスト・ガント共通）：Core＝赤 #e03131、Operational＝紫 #7048e8（2026-11-08 に青から変更）、Strategic＝緑 #2f9e44、Divest＝灰 #868e96、Adhoc＝黄 #f5b800。コード内のキーは core/infra/ambition/bull（名前を変えない）。
- タスクの重要度・必要度・緊急度は6段階で **1が最も高い**（1〜3が高）。IN/OUT_Navi（旧 購入分析）は逆で6が高い（統一するかは未確定）。
- 用語：「Adhoc」「タスクリスト」「買い物リスト」「IN/OUT_Navi」（旧 購入分析。品の状態は Wants／Buy／Hold／Clutter／Sold）。

## 速さ（第一優先）
- 動作の速さを最優先する（Dr. Ishida の指示）。画面の描き直しは必要な範囲だけにし、操作中にファイルの書き込みで画面を止めない（`docs/SPEC.md` 6.1）。
- マップは画面内のノードだけを描く（`redraw` の間引き）。全部のノードが描かれている前提のコードを書かない（実際に描いたものは `_drawn_ids`）。

## データの互換（壊さない）
- データは1つの JSON ファイルにすべて入れる。同じフォルダに同内容の `<名前>.backup.json` を書く。
- 読んだ未知の属性は消さずに書き戻す。データ形式を変えるときは古いデータの読み替えを入れる。
- Android版は同じファイルの `view.groceries` だけを書き換える。**PC版の買い物リストの仕様を変えたら Android版も合わせ、`app/build.gradle` の versionCode を1つ上げる**。
- 個人の実データ（`*.json` のデータファイル）はリポジトリに入れない（`samples/` のダミーだけ）。

## Android版
- ラムダ式・メソッド参照を使わない（Gradle なしのビルドで動かなくなる。匿名クラスで書く）。
- ビルドは `android/MindNaviShopping/tools/build_apk.sh`（手順は `docs/SPEC.md` 11章）。
- 署名の鍵とパスワードは `android/MindNaviShopping/signing/` にある（2026-11-08 に新しい鍵を作り、Dr. Ishida の決定でリポジトリに保管）。**この鍵を作り直したり消したりしない**（作り直すと、入っているアプリに上書きできなくなる）。
- 配布：GitHub の「Actions」→「配布ファイルを作る」で、PC版 `mind_navi.py` と APK を Releases ページに置く（`docs/SPEC.md` 11.6）。

## 名称（旧称 TaskMap）
- 2026-11-08 に TaskMap から Mind_Navi へ名前を変えた。新しく書くものはすべて Mind_Navi にする。
- 旧名のまま残すもの（変えると既存データと食い違う）：Google カレンダーの照合キー `taskmap_id`、ICS の UID `@taskmap`、旧版からの取り込み元 `~/.taskmap_shopping.json` など4つ、起動時に旧設定を引き継ぐ処理（`migrate_old_local_files`・`_migrate_data_dir`）、署名の鍵の別名 `taskmap`（新しい鍵でも同じ別名）、互換用の別名 `TaskMap = MindNavi`。詳細は `docs/SPEC.md` 冒頭。

## 既知の課題
`docs/SPEC.md` の 9章（未確認事項・ヘルプとコードの食い違い）を参照。
