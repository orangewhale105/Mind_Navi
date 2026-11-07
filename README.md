# Mind_Navi

目標とタスクをマップ形式で整理し、カレンダー・タスクリスト・買い物リストまでを1つのデータファイルで管理するソフト。

## 起動（PC版）
```
python desktop/mind_navi.py                 # 前回の状態で開く／新規
python desktop/mind_navi.py データ.json      # ファイルを指定して開く
```
Windows では Python（公式インストーラー）を入れれば追加なしで動きます。任意機能のライブラリは `docs/SPEC.md` の10章。

## 最新版にする
GitHub Desktop で「Fetch origin」→「Pull origin」を押してから起動します。

## フォルダ
- `desktop/` PC版
- `android/` Android版 買い物リスト
- `installer/` Windows インストーラー（未着手）
- `docs/SPEC.md` 仕様書
- `samples/` ダミーデータ
- `tests/` 自動テスト
