# Repository Guidelines

## プロジェクト構成とモジュール構成
- `src/voicevox_cli/` にパッケージ本体がまとまり、`cli.py` がエントリポイント、`pipeline.py` が合成フロー、`playback.py` が再生バックエンドです。
- 追加モジュールは `src/voicevox_cli/` 配下に配置し、対応するテストを `tests/` に新設してください（現状未作成）。
- ルート直下の `README.md` が利用者向け案内、`pyproject.toml` がメタデータと依存定義のソースです。

## ビルド・テスト・開発コマンド
- `uv pip install -e .[dev]` で開発依存込みで導入します。音声再生に simpleaudio が必要なら `.[audio]` を併用。
- `uvx --from . voicevox-cli --text "テスト"` でソースから CLI を即実行できます。インストール済みなら単に `voicevox-cli ...`。
- テストは `pytest` を採用予定です。追加後は `pytest -q` を実行できるよう `pyproject.toml` に設定してください。
- simpleaudio を利用する場合は `uv pip install -e .[audio]` を実行し、OS 側のサウンドデバイスを確認してください。

## コーディングスタイルと命名規約
- PEP 8 と型ヒントを基本とし、公開関数には引数・戻り値の型を明示します。
- ロガーは `logging.getLogger(__name__)` を使用し、INFO 以上で動作が追えるようにしてください。
- CLI に追加するオプションは短縮形も検討し、`VOICEVOX_CLI_XXX` 形式の環境変数と整合させます。
- 非同期コードではタスクキャンセルを忘れず、`asyncio.gather(..., return_exceptions=True)` などで資源を回収します。

## テストガイドライン
- 文分割、HTTP 通信、再生制御それぞれに単体テストを用意し、VOICEVOX ENGINE 呼び出しはモック化してください。
- 例外発生時のリトライやタスクキャンセルもテスト対象です。回帰防止のためにシナリオテストを追加します。
- simpleaudio など OS 依存部分は条件付きでスキップし、エラー時は代替バックエンドが選択されることを確認します。

## コミット・Pull Request ガイドライン
- コミットメッセージは命令形・現在形で 50 文字目安の概要を付け、必要なら本文で背景を補足します。
- PR には変更概要、テスト結果、VOICEVOX ENGINE への影響（必要なバージョンや追加設定）を記載します。
- ログレベルや環境変数の変更時は README/AGENTS の更新をセットにし、レビュワーが動作確認しやすい情報を提示してください。
