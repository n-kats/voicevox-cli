# voicevox-cli

VOICEVOX ENGINE にテキストを送り、文ごとにストリーミング再生するための軽量 CLI です。  
`ffplay` (FFmpeg) を優先利用し、見つからない場合は `simpleaudio` にフォールバックします。

## 必要環境

- Python 3.11 以上
- VOICEVOX ENGINE がローカルまたはネットワーク上で稼働していること
- 音声再生:
  - 推奨: FFmpeg (`ffplay` コマンドが利用可能であること)
  - 代替: `simpleaudio` をインストール (`uv pip install -e .[audio]`) し、OS 側の ALSA/CoreAudio などが利用可能であること

## インストール

```bash
# 開発用クローンでの利用
uv pip install -e .

# simpleaudio を使う場合
uv pip install -e .[audio]
```

`uvx` からワンショットで呼び出したい場合は、同ディレクトリで次のように実行します。

```bash
uvx --from . voicevox-cli --text "こんにちは"
```

## 使い方

```bash
voicevox-cli --file input.txt
voicevox-cli --text "ずんだもんがしゃべります"
voicevox-cli -f script.md --player ffplay
```

- `--file` / `-f`: UTF-8 テキストファイルを読み上げます。`-` を指定すると標準入力を利用できます。
- `--text` / `-t`: コマンドラインから直接テキストを渡します。
- `--player`: `auto` (既定) / `ffplay` / `simpleaudio` / `none` から再生バックエンドを選択。`auto` は `ffplay` → `simpleaudio` → `none` の順で判断します。
- `--ffplay-path`: PATH に `ffplay` が無い場合に明示的にパスを指定します。
- そのほか、速度やピッチなど VOICEVOX ENGINE の AudioQuery パラメータも CLI で調整できます。

### 環境変数

以下の環境変数で CLI 引数の既定値を上書きできます（CLI 引数が指定されている場合はそちらが優先されます）。

| 環境変数名           | 内容                         | 例                    |
|----------------------|------------------------------|-----------------------|
| `VOICEVOX_CLI_ENGINE_URL`   | VOICEVOX ENGINE のベース URL | `http://127.0.0.1:50021` |
| `VOICEVOX_CLI_SPEED` | `speedScale` の既定値        | `1.15`                |
| `VOICEVOX_CLI_VOLUME`| `volumeScale` の既定値       | `0.9`                 |

## トラブルシューティング

- simpleaudio の安定性を確認したい場合は `python scripts/check_simpleaudio.py --repeats 5` を実行してください。ここでクラッシュする場合は FFmpeg を導入し `--player ffplay` を利用するか、`--player none` で再生をスキップしてください。
- VOICEVOX ENGINE との通信に失敗した場合は URL とスピーカー ID を確認し、エンジンが起動しているかを再確認してください。

## 開発

```bash
uv pip install -e .[dev]
pytest
python scripts/check_simpleaudio.py --repeats 3
```

コントリビューション時は `AGENTS.md` のガイドラインに従ってください。
