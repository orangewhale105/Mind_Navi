# 変更履歴

新しいものを上に書く。詳しい経緯は `docs/SPEC.md` の12章。

## 2026-11-08 配布ファイルを Releases ページからダウンロードできるように
- GitHub Actions のワークフロー「配布ファイルを作る」（`.github/workflows/release.yml`）を追加。PC版 `mind_navi.py` と署名付き Android版 APK を Releases ページに置く。
- Android版の署名の鍵を新しく作り、`android/MindNaviShopping/signing/` に保管（利用者の決定。移行時の「鍵をリポジトリに入れない」を変更）。元の鍵の版には上書きできないため、一度アンインストールして入れ直す。詳細は `docs/SPEC.md` 11.4・11.6。

## 2026-11-08 名称を Mind_Navi に変更（旧称 TaskMap）
- PC版：`desktop/taskmap.py` → `desktop/mind_navi.py`。画面の表示名、データファイルの app 欄、PC ごとの設定ファイル（`~/.mind_navi_*`）、Google ドライブのデータフォルダ（`Mind_Navi`）を新しい名前に。
- PC版：起動時に旧設定（`~/.taskmap_*`）とバックアップを新しい名前へコピー。データフォルダが `TaskMap` なら同じ場所の `Mind_Navi` へファイルをコピーして切り替え（元は残す）。旧名のデータファイルもそのまま開ける。
- Android版 1.2（versionCode 3）：`android/MindNaviShopping/`、識別名 `jp.mindnavi.shopping`、アプリ名「Mind_Navi 買い物リスト」。旧版には上書きできないため入れ直しが必要。
- Google カレンダーの照合キー・ICS の UID は、同期済みの予定と重複させないため旧名のまま。

## 2026-11-07 GitHub へ移行
- チャットでの開発から GitHub（プライベートリポジトリ）＋ Claude に移行。
- 構成を `desktop/`・`android/`・`installer/`・`docs/`・`samples/`・`tests/` に整理。
- 仕様書を `docs/SPEC.md` に置き、正本とした。開発ルールを `CLAUDE.md` に記載。
- Android版の署名の鍵とパスワードをリポジトリから除外。ビルドスクリプトは環境変数で鍵を受け取る形に変更（現在の名前は `MIND_NAVI_KEYSTORE`・`MIND_NAVI_KS_PASS`）。
- データの読み書き・バックアップ・CLI出力の自動テストを追加。

## PC版 3.6 ／ Android版 1.1（2026-11-07 時点）
移行前の内容。`docs/SPEC.md` 12章を参照。
