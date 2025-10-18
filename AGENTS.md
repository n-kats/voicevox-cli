# Repository Guidelines

## Project Structure & Module Organization
- `sample.py`: repository内で CLI を即試せるサンプルスクリプト。コア処理は `src/voicevox_cli/` に実装。
- `pyproject.toml`: source of truth for metadataと依存の登録先。HTTP/AIO 用の `aiohttp` を通常依存に追加し、`simpleaudio` など OS 依存の再生ドライバは `[project.optional-dependencies.audio]` で管理。
- Expand into `src/voicevox_cli/` (create the package when needed) and mirror tests under `tests/`.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate`: create and activate the virtual environment.
- `python -m pip install -e .[dev]`: install the project in editable mode; audio 再生用に `.[audio]` を併せて入れる場合は環境に応じて判断。
- `python sample.py --text "こんにちは"`: VOICEVOX ENGINE (既定: `http://127.0.0.1:50021`) に対してストリーミング処理を実行。
- `uvx --from . voicevox-cli --text "こんにちは"`: パッケージ経由で CLI を呼ぶ。開発中は `python -m voicevox_cli.cli --text ...` も可。

## Coding Style & Naming Conventions
- Follow PEP 8 with four-space indentation, snake_case for functions and variables, and UPPER_CASE for constants such as `VOICEVOX_URL_DEFAULT`.
- Add type hints on public functions and explicit return types on coroutines.
- Keep modules cohesive—split networking helpers, audio utilities, and CLI wiring into dedicated files once `src/voicevox_cli/` exists.
- Run `python -m ruff check .` (or your preferred linter) and track config in `pyproject.toml`.

## Testing Guidelines
- Adopt `pytest` (declare it under `project.optional-dependencies.dev`) and mirror modules in `tests/`.
- Name test files `test_<module>.py` and mark async cases with `pytest.mark.asyncio`.
- Cover sentence splitting edge cases, HTTP layer stubs, and audio queueing logic; mock VOICEVOX calls with `aiohttp` helpers.
- Run `pytest -q` locally and surface coverage gaps in PR descriptions.

## Commit & Pull Request Guidelines
- Use present-tense, imperative commit subjects (`Add streaming retries`) and wrap at ~72 characters.
- Group related changes together; explain non-obvious decisions in the body.
- Open PRs with a short summary, testing checklist, linked issues, and media when behavior changes.
- Ask for review once lint and tests pass, and flag risky areas (networking, async concurrency).

## VOICEVOX Setup Notes
- Run a VOICEVOX Engine locally for end-to-end testing; set `VOICEVOX_URL` if you use a custom host.
- Keep API keys or proprietary voices out of Git; use environment variables or ignored config files.
- CLI playback は `--player auto|ffplay|simpleaudio|none` で切替可能。FFmpeg が導入済みなら `--player ffplay`（または既定の `auto`）が最も安定。
- simpleaudio の挙動が不安定な環境では `python scripts/check_simpleaudio.py --repeats 5` で単体検証し、問題があれば `--player ffplay` や `--player none` を選択。
