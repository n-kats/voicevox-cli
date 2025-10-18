from __future__ import annotations

import asyncio
import logging
import re
from asyncio import Semaphore

import aiohttp
import requests

from .playback import PlaybackBackend, play_wav_bytes, resolve_playback_backend

VOICEVOX_URL_DEFAULT = "http://127.0.0.1:50021"
_SENTENCE_PATTERN = re.compile(r"[^。．.!！？\?]+[。．.!！？\?]?")
_LOGGER = logging.getLogger(__name__)
_SNIPPET_LIMIT = 80


def _shorten(sentence: str) -> str:
    return sentence if len(sentence) <= _SNIPPET_LIMIT else f"{sentence[:_SNIPPET_LIMIT - 3]}..."


def split_sentences(text: str, *, max_len: int = 200) -> list[str]:
    """日本語混在のテキストを安全な長さで文分割する。"""
    normalized = text.replace("\r\n", "\n")
    lines = [line.strip() for line in normalized.split("\n") if line.strip()]
    sentences: list[str] = []

    for line in lines:
        if len(line) <= max_len:
            sentences.append(line)
            continue

        for match in _SENTENCE_PATTERN.findall(line):
            segment = match.strip()
            if not segment:
                continue
            if len(segment) <= max_len:
                sentences.append(segment)
                continue

            chunks = re.split(r"[、,]\s*", segment)
            buffer = ""
            for chunk in chunks:
                chunk = chunk.strip()
                if not chunk:
                    continue
                if len(buffer) + len(chunk) + (1 if buffer else 0) <= max_len:
                    buffer = f"{buffer}、{chunk}" if buffer else chunk
                    continue

                if buffer:
                    sentences.append(buffer)
                    buffer = ""

                if len(chunk) <= max_len:
                    buffer = chunk
                    continue

                for index in range(0, len(chunk), max_len):
                    part = chunk[index : index + max_len]
                    if part:
                        sentences.append(part)

            if buffer:
                sentences.append(buffer)

    return sentences


async def audio_query(
    session: aiohttp.ClientSession,
    base_url: str,
    text: str,
    speaker: int,
    overrides: dict[str, float | None] | None = None,
) -> dict:
    """VOICEVOX の /audio_query を呼び出しクエリ JSON を取得する。"""
    params = {"text": text, "speaker": str(speaker)}
    async with session.post(f"{base_url}/audio_query", params=params) as resp:
        resp.raise_for_status()
        query = await resp.json()

    if overrides:
        for key, value in overrides.items():
            if value is not None:
                query[key] = value

    return query


async def synthesis(
    session: aiohttp.ClientSession,
    base_url: str,
    query_json: dict,
    speaker: int,
) -> bytes:
    """VOICEVOX の /synthesis を呼び出し WAV バイト列を取得する。"""
    params = {"speaker": str(speaker)}
    async with session.post(f"{base_url}/synthesis", params=params, json=query_json) as resp:
        resp.raise_for_status()
        return await resp.read()


async def speak_streaming(
    text: str,
    *,
    base_url: str = VOICEVOX_URL_DEFAULT,
    speaker: int = 1,
    speed: float | None = None,
    volume: float | None = None,
    pitch: float | None = None,
    intonation: float | None = None,
    prefetch: int = 3,
    max_len: int = 200,
    connector_limit: int = 8,
    playback_backend: PlaybackBackend = "auto",
    ffplay_path: str | None = None,
) -> None:
    """文ごとに先読みしながら VOICEVOX で読み上げる。"""
    sentences = split_sentences(text, max_len=max_len)
    if not sentences:
        return

    backend, resolved_ffplay_path = resolve_playback_backend(playback_backend, ffplay_path)
    if _LOGGER.isEnabledFor(logging.INFO):
        _LOGGER.info("合成対象の文数: %d", len(sentences))
        if backend == "none":
            _LOGGER.warning("再生バックエンドが利用できないため、音声は再生されません。")
        else:
            _LOGGER.info("使用する再生バックエンド: %s", backend)

    overrides = {
        "speedScale": speed,
        "volumeScale": volume,
        "pitchScale": pitch,
        "intonationScale": intonation,
    }

    connector = aiohttp.TCPConnector(limit=connector_limit)
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=300)
    semaphore = Semaphore(prefetch)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        async def synthesize(sentence: str) -> bytes:
            retries = 3
            delay = 0.5
            for attempt in range(1, retries + 1):
                try:
                    async with semaphore:
                        query = await audio_query(session, base_url, sentence, speaker, overrides)
                        return await synthesis(session, base_url, query, speaker)
                except aiohttp.ServerDisconnectedError as err:
                    if attempt == retries:
                        raise
                    if _LOGGER.isEnabledFor(logging.WARNING):
                        _LOGGER.warning(
                            "リトライ %d/%d: VOICEVOX ENGINE との通信が切断されました (%s) - %s",
                            attempt,
                            retries,
                            _shorten(sentence),
                            err,
                        )
                    await asyncio.sleep(delay)
                    delay *= 2
                except aiohttp.ClientConnectionError as err:
                    if attempt == retries:
                        raise
                    if _LOGGER.isEnabledFor(logging.WARNING):
                        _LOGGER.warning(
                            "リトライ %d/%d: VOICEVOX ENGINE への接続に失敗しました (%s) - %s",
                            attempt,
                            retries,
                            _shorten(sentence),
                            err,
                        )
                    await asyncio.sleep(delay)
                    delay *= 2

        tasks: list[tuple[str, asyncio.Task[bytes]]] = [
            (sentence, asyncio.create_task(synthesize(sentence))) for sentence in sentences
        ]

        try:
            total = len(tasks)
            for index, (sentence, task) in enumerate(tasks, start=1):
                if _LOGGER.isEnabledFor(logging.INFO):
                    _LOGGER.info("再生準備中 %d/%d: %s", index, total, _shorten(sentence))
                wav_bytes = await task
                if backend != "none":
                    if _LOGGER.isEnabledFor(logging.DEBUG):
                        _LOGGER.debug("再生開始 %d/%d (%d bytes)", index, total, len(wav_bytes))
                    play_wav_bytes(
                        wav_bytes,
                        backend=backend,
                        ffplay_path=resolved_ffplay_path,
                    )
                    if _LOGGER.isEnabledFor(logging.DEBUG):
                        _LOGGER.debug("再生完了 %d/%d", index, total)
        finally:
            pending = [task for _, task in tasks if not task.done()]
            for task in pending:
                task.cancel()
            if tasks:
                await asyncio.gather(*(task for _, task in tasks), return_exceptions=True)


def audio_query_sync(
    base_url: str,
    text: str,
    speaker: int,
    overrides: dict[str, float | None] | None = None,
) -> dict:
    """同期版の /audio_query 呼び出し。"""
    params = {"text": text, "speaker": str(speaker)}
    response = requests.post(f"{base_url}/audio_query", params=params, timeout=30)
    response.raise_for_status()
    query = response.json()
    if overrides:
        for key, value in overrides.items():
            if value is not None:
                query[key] = value
    return query


def synthesis_sync(
    base_url: str,
    query_json: dict,
    speaker: int,
) -> bytes:
    """同期版の /synthesis 呼び出し。"""
    params = {"speaker": str(speaker)}
    response = requests.post(
        f"{base_url}/synthesis",
        params=params,
        json=query_json,
        timeout=120,
    )
    response.raise_for_status()
    return response.content


def speak_streaming_sync(
    text: str,
    *,
    base_url: str = VOICEVOX_URL_DEFAULT,
    speaker: int = 1,
    speed: float | None = None,
    volume: float | None = None,
    pitch: float | None = None,
    intonation: float | None = None,
    prefetch: int = 3,
    max_len: int = 200,
    connector_limit: int = 8,
    playback_backend: PlaybackBackend = "auto",
    ffplay_path: str | None = None,
) -> None:
    """同期版のストリーミング読み上げ。HTTP コールを逐次実行する。"""
    sentences = split_sentences(text, max_len=max_len)
    if not sentences:
        return

    backend, resolved_ffplay_path = resolve_playback_backend(playback_backend, ffplay_path)
    if _LOGGER.isEnabledFor(logging.INFO):
        _LOGGER.info("合成対象の文数: %d", len(sentences))
        if backend == "none":
            _LOGGER.warning("再生バックエンドが利用できないため、音声は再生されません。")
        else:
            _LOGGER.info("使用する再生バックエンド: %s", backend)

    overrides = {
        "speedScale": speed,
        "volumeScale": volume,
        "pitchScale": pitch,
        "intonationScale": intonation,
    }

    total = len(sentences)
    for index, sentence in enumerate(sentences, start=1):
        if _LOGGER.isEnabledFor(logging.INFO):
            _LOGGER.info("再生準備中 %d/%d: %s", index, total, _shorten(sentence))
        query = audio_query_sync(base_url, sentence, speaker, overrides)
        wav_bytes = synthesis_sync(base_url, query, speaker)
        if backend != "none":
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug("再生開始 %d/%d (%d bytes)", index, total, len(wav_bytes))
            play_wav_bytes(
                wav_bytes,
                backend=backend,
                ffplay_path=resolved_ffplay_path,
            )
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug("再生完了 %d/%d", index, total)
