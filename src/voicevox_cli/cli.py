from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
import os
from typing import Sequence
import logging

import aiohttp

from .pipeline import VOICEVOX_URL_DEFAULT, speak_streaming, speak_streaming_sync

ENV_ENGINE_URL = "VOICEVOX_CLI_ENGINE_URL"
ENV_SPEED = "VOICEVOX_CLI_SPEED"
ENV_VOLUME = "VOICEVOX_CLI_VOLUME"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="voicevox-cli",
        description="VOICEVOX ENGINE と連携してテキストをストリーミング再生する CLI ツール。",
    )
    parser.add_argument("-t", "--text", help="読み上げるテキスト（--file より優先）")
    parser.add_argument("-f", "--file", help="UTF-8 テキストファイルのパス（- で標準入力）")
    parser.add_argument(
        "--url",
        help=(
            f"VOICEVOX ENGINE のベース URL（既定: {VOICEVOX_URL_DEFAULT}。"
            f"環境変数 {ENV_ENGINE_URL} でも指定可）"
        ),
    )
    parser.add_argument("--speaker", type=int, default=1, help="話者 ID（例: 1 = ずんだもん/ノーマル）")
    parser.add_argument(
        "--speed",
        type=float,
        help=f"speedScale（例: 1.2。環境変数 {ENV_SPEED} でも指定可）",
    )
    parser.add_argument(
        "--volume",
        type=float,
        help=f"volumeScale（例: 1.0。環境変数 {ENV_VOLUME} でも指定可）",
    )
    parser.add_argument("--pitch", type=float, help="pitchScale（例: 0.0）")
    parser.add_argument("--intonation", type=float, help="intonationScale（例: 1.0）")
    parser.add_argument("--prefetch", type=int, default=3, help="同時に先読みする文の数")
    parser.add_argument("--max-len", type=int, default=200, help="1 文の最大長（安全分割用）")
    parser.add_argument(
        "--connector-limit",
        type=int,
        default=8,
        help="同時接続の上限（VOICEVOX ENGINE への同時接続数）",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="INFO レベルのログを表示して進行状況を追跡します。",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="詳細なデバッグログを表示します（--verbose を含む）。",
    )
    parser.add_argument(
        "--player",
        choices=["auto", "simpleaudio", "ffplay", "none"],
        default="auto",
        help="再生バックエンドを選択します（auto は ffplay → simpleaudio → none の順で使用）。",
    )
    parser.add_argument(
        "--ffplay-path",
        help="ffplay のパスを明示指定します（PATH に存在しない場合）。",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="内部で同期 API を使用して実行します（`asyncio` ループとの衝突を避けたい場合に利用）。",
    )
    return parser


def _parse_float_env(name: str, value: str) -> float:
    try:
        return float(value)
    except ValueError as err:
        raise ValueError(f"{name} は数値で指定してください: {value}") from err


def _apply_env_overrides(args: argparse.Namespace) -> None:
    """環境変数で指定された設定を反映する。CLI 引数が優先。"""
    env = os.environ

    url_env = env.get(ENV_ENGINE_URL)
    legacy_url_env = env.get("VOICEVOX_CLI_URL")
    if args.url:
        resolved_url = args.url
    elif url_env:
        resolved_url = url_env
    elif legacy_url_env:
        logging.getLogger(__name__).warning(
            "VOICEVOX_CLI_URL は将来のバージョンで削除予定です。VOICEVOX_CLI_ENGINE_URL を使用してください。"
        )
        resolved_url = legacy_url_env
    else:
        resolved_url = VOICEVOX_URL_DEFAULT
    args.url = resolved_url

    if args.speed is None:
        speed_env = env.get(ENV_SPEED)
        if speed_env:
            args.speed = _parse_float_env(ENV_SPEED, speed_env)

    if args.volume is None:
        volume_env = env.get(ENV_VOLUME)
        if volume_env:
            args.volume = _parse_float_env(ENV_VOLUME, volume_env)


def _load_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text

    if args.file:
        if args.file == "-":
            data = sys.stdin.read()
            if data.strip():
                return data
            raise ValueError("標準入力からテキストを受け取れませんでした。")

        file_path = Path(args.file).expanduser()
        if not file_path.is_file():
            raise FileNotFoundError(f"テキストファイルが見つかりません: {file_path}")
        return file_path.read_text(encoding="utf-8")

    data = sys.stdin.read()
    if data.strip():
        return data

    raise ValueError("読み上げるテキストを --text / --file / 標準入力のいずれかで指定してください。")


async def _run(text: str, args: argparse.Namespace) -> None:
    logger = logging.getLogger(__name__)
    if args.player == "none" and (args.verbose or args.debug):
        logger.warning("音声再生をスキップします (--player none)。")
    await speak_streaming(
        text,
        base_url=args.url,
        speaker=args.speaker,
        speed=args.speed,
        volume=args.volume,
        pitch=args.pitch,
        intonation=args.intonation,
        prefetch=args.prefetch,
        max_len=args.max_len,
        connector_limit=args.connector_limit,
        playback_backend=args.player,
        ffplay_path=args.ffplay_path,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()

    arg_list = list(argv) if argv is not None else sys.argv[1:]
    if not arg_list:
        parser.print_help()
        return 0

    args = parser.parse_args(arg_list)

    try:
        _apply_env_overrides(args)
    except ValueError as err:
        parser.error(str(err))

    log_level = logging.WARNING
    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s:%(name)s:%(message)s")

    try:
        text = _load_text(args)
        if args.sync:
            if args.player == "none" and (args.verbose or args.debug):
                logging.getLogger(__name__).warning("音声再生をスキップします (--player none)。")
            speak_streaming_sync(
                text,
                base_url=args.url,
                speaker=args.speaker,
                speed=args.speed,
                volume=args.volume,
                pitch=args.pitch,
                intonation=args.intonation,
                prefetch=args.prefetch,
                max_len=args.max_len,
                connector_limit=args.connector_limit,
                playback_backend=args.player,
                ffplay_path=args.ffplay_path,
            )
        else:
            asyncio.run(_run(text, args))
    except KeyboardInterrupt:
        return 130
    except FileNotFoundError as err:
        parser.error(str(err))
    except ValueError as err:
        parser.error(str(err))
    except aiohttp.ClientError as err:
        parser.exit(1, f"VOICEVOX ENGINE への接続に失敗しました: {err}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
