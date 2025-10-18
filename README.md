# voicevox-cli

VOICEVOX ENGINE にテキストを送り、文単位でストリーミング再生するためのシンプルな CLI です。  
`ffplay` (FFmpeg) を優先し、見つからない場合は `simpleaudio` を自動で利用します。

## セットアップ

1. Python 3.11 以上と VOICEVOX ENGINE（例: `voicevox_engine --use_gpu 0`）を起動しておきます。  
   既定の接続先は `http://127.0.0.1:50021` です。
2. FFmpeg（`ffplay`）をインストールします。Linux なら `sudo apt install ffmpeg`、macOS なら `brew install ffmpeg` など、環境に応じたパッケージマネージャーを利用してください。PATH に `ffplay` が存在することを確認します。
3. CLI のインストール方法は用途に合わせて選べます。

```bash
# 公開リポジトリから最新リリースを取得
uv tool install git+https://github.com/n-kats/voicevox-cli

# または pip を使う場合
pip install git+https://github.com/n-kats/voicevox-cli

# ローカル開発クローンで利用する場合
uv pip install -e .

# 音声再生に simpleaudio を使いたい場合
uv pip install -e .[audio]

# ワンショット実行（カレントディレクトリのソースから）
uvx --from . voicevox-cli --text "こんにちは"
```

## 使い方

```bash
voicevox-cli --text "ずんだもんがしゃべります"
voicevox-cli -f script.md
voicevox-cli               # 引数がなければヘルプを表示
```

- `-t/--text`: 直接文字列を渡します。  
- `-f/--file`: UTF-8 テキストファイルを指定します（`-` で標準入力）。  
- `--speed` / `--volume`: VOICEVOX ENGINE の `speedScale` / `volumeScale` を上書き。

### 環境変数による既定値の変更

| 変数名 | 内容 | 備考 |
| --- | --- | --- |
| `VOICEVOX_CLI_ENGINE_URL` | VOICEVOX ENGINE のベース URL | 例: `http://127.0.0.1:50021` |
| `VOICEVOX_CLI_SPEED` | `speedScale` の既定値 | 引数が優先されます |
| `VOICEVOX_CLI_VOLUME` | `volumeScale` の既定値 | 引数が優先されます |

## トラブルシューティング

- 「Session is closed」などの接続エラーが出る場合は VOICEVOX ENGINE の起動状態と URL を確認し、リトライで解消しない場合はログを併せて調査してください。
- simpleaudio 利用時にクラッシュする／音が出ない場合は `--player ffplay` へ切り替えるか、`--player none` で再生を抑止してください。

## 開発フロー

```bash
uv pip install -e .[dev]
pytest
```

PR を送る際は `AGENTS.md` のガイドラインに従い、再生バックエンドや VOICEVOX ENGINE への影響があれば必ず記載してください。

## 予備機能: `--player` オプション

`--player` で再生バックエンドを切り替えられます。既定は `auto` で、`ffplay` が見つかれば自動的に使用します。

```bash
voicevox-cli -f script.md --player ffplay          # 明示的に ffplay を使う（PATH にない場合は --ffplay-path で指定）
voicevox-cli -t "テキスト" --player simpleaudio     # simpleaudio を使う（別途インストールが必要）
voicevox-cli --text "テキスト" --player none        # 音声を再生せず合成だけ行う
```

- `ffplay`: もっとも安定した再生方法です。
- `simpleaudio`: オプション依存。環境によってはサウンド設定が必要だったり不安定になる場合があります。
- `none`: 再生をスキップします。音声デバイスがない環境や CI で便利です。
