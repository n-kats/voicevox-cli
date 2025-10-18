"""VOICEVOX CLI ツールのパッケージ。"""

from .pipeline import VOICEVOX_URL_DEFAULT, speak_streaming, speak_streaming_sync

__all__ = ["VOICEVOX_URL_DEFAULT", "speak_streaming", "speak_streaming_sync"]
__version__ = "0.1.0"
