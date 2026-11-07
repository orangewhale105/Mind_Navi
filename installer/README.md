# Windows インストーラー（未着手）

方式は未確定。候補：PyInstaller で `desktop/mind_navi.py` を exe にまとめ、Inno Setup でセットアップ.exe にする。

- Windows 用の exe は Windows 上でビルドする必要がある（GitHub 上の自動ビルド、または Dr. Ishida の PC でスクリプト実行）。
- 署名なしのインストーラーは実行時に Windows の警告が出る。販売時はコード署名証明書（有料）を検討。
