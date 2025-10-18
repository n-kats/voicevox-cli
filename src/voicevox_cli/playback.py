from __future__ import annotations

import logging
import shutil
import subprocess
import wave
from io import BytesIO
from typing import Literal

_LOGGER = logging.getLogger(__name__)

PlaybackBackend = Literal["auto", "simpleaudio", "ffplay", "none"]

try:
    import simpleaudio as sa  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    sa = None  # type: ignore[assignment]

_SIMPLEAUDIO_AVAILABLE = sa is not None


def resolve_playback_backend(preferred: PlaybackBackend, ffplay_path: str | None = None) -> tuple[str, str | None]:
    """希望するバックエンドを基に実際に利用するバックエンドを決定する。"""
    if preferred == "auto":
        path = ffplay_path or shutil.which("ffplay")
        if path:
            return "ffplay", path
        if _SIMPLEAUDIO_AVAILABLE:
            return "simpleaudio", None
        return "none", None

    if preferred == "ffplay":
        path = ffplay_path or shutil.which("ffplay")
        if not path:
            raise RuntimeError("ffplay が見つかりません。--ffplay-path でパスを指定してください。")
        return "ffplay", path

    if preferred == "simpleaudio":
        if not _SIMPLEAUDIO_AVAILABLE:
            raise RuntimeError("simpleaudio が利用できません。`pip install simpleaudio` を確認してください。")
        return "simpleaudio", None

    if preferred == "none":
        return "none", None

    raise ValueError(f"未知の再生バックエンド指定です: {preferred}")


def play_wav_bytes(
    wav_bytes: bytes,
    *,
    backend: PlaybackBackend = "auto",
    ffplay_path: str | None = None,
) -> None:
    """WAV バイト列を指定バックエンドで再生する。"""
    backend_resolved, path = resolve_playback_backend(backend, ffplay_path)

    if backend_resolved == "none":
        _LOGGER.debug("音声再生をスキップしました（backend=none）。")
        return

    if backend_resolved == "ffplay":
        _play_with_ffplay(wav_bytes, executable=path)
        return

    if backend_resolved == "simpleaudio":
        _play_with_simpleaudio(wav_bytes)
        return

    raise AssertionError(f"未処理のバックエンド: {backend_resolved}")


def _play_with_ffplay(wav_bytes: bytes, *, executable: str | None) -> None:
    if not executable:
        raise RuntimeError("ffplay のパスが解決できませんでした。")

    process = subprocess.Popen(
        [executable, "-autoexit", "-nodisp", "-loglevel", "error", "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    assert process.stdin is not None
    process.stdin.write(wav_bytes)
    process.stdin.close()

    process.wait()


def _play_with_simpleaudio(wav_bytes: bytes) -> None:
    if sa is None:
        raise RuntimeError("simpleaudio が利用できません。")

    with wave.open(BytesIO(wav_bytes), "rb") as wave_file:
        frames = wave_file.readframes(wave_file.getnframes())
        channels = wave_file.getnchannels()
        sample_width = wave_file.getsampwidth()
        frame_rate = wave_file.getframerate()

    if not frames:
        _LOGGER.warning("空の音声フレームを受信したため再生をスキップします。")
        return

    wave_obj = sa.WaveObject(frames, channels, sample_width, frame_rate)
    play_obj = wave_obj.play()
    play_obj.wait_done()
