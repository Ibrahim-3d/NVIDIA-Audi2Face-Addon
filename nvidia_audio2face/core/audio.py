"""Audio loading, validation, resampling, and chunking."""
import wave
import struct
from pathlib import Path
from typing import Optional

import numpy as np

from .. import constants


class AudioError(Exception):
    """Raised when audio validation or processing fails."""
    pass


def load_wav(filepath: str) -> tuple[int, np.ndarray, int]:
    """Load a WAV file and return (sample_rate, data_int16, num_channels).

    Raises AudioError if the file is invalid or unsupported.
    """
    path = Path(filepath)
    if not path.exists():
        raise AudioError(f"Audio file not found: {filepath}")
    if path.suffix.lower() != ".wav":
        raise AudioError("Unsupported audio format. Please use WAV (PCM 16-bit).")

    try:
        with wave.open(str(path), "rb") as wf:
            sample_rate = wf.getframerate()
            num_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            num_frames = wf.getnframes()

            if sample_width != 2:
                raise AudioError(
                    f"Audio must be 16-bit PCM WAV. Current: {sample_width * 8}-bit"
                )
            if num_channels > 2:
                raise AudioError(
                    f"Only mono or stereo audio supported. File has {num_channels} channels."
                )

            raw_data = wf.readframes(num_frames)
    except wave.Error as e:
        raise AudioError(f"Cannot read WAV file: {e}")

    # Convert bytes to int16 numpy array
    data = np.frombuffer(raw_data, dtype=np.int16)

    return sample_rate, data, num_channels


def convert_to_mono(data: np.ndarray, num_channels: int) -> np.ndarray:
    """Convert stereo audio to mono by averaging channels."""
    if num_channels == 1:
        return data
    # Interleaved stereo: L0 R0 L1 R1 ...
    left = data[0::2].astype(np.int32)
    right = data[1::2].astype(np.int32)
    return ((left + right) // 2).astype(np.int16)


def resample(data: np.ndarray, original_rate: int, target_rate: int = 16000) -> np.ndarray:
    """Resample audio using linear interpolation (numpy only, no scipy)."""
    if original_rate == target_rate:
        return data
    ratio = target_rate / original_rate
    new_length = int(len(data) * ratio)
    if new_length == 0:
        return data
    x_old = np.linspace(0, 1, len(data))
    x_new = np.linspace(0, 1, new_length)
    return np.interp(x_new, x_old, data.astype(np.float64)).astype(np.int16)


def validate_duration(data: np.ndarray, sample_rate: int) -> None:
    """Validate audio duration is within acceptable range."""
    duration = len(data) / sample_rate
    if duration > constants.AUDIO_MAX_DURATION_SECONDS:
        raise AudioError(
            f"Audio exceeds 5 minute limit ({duration:.1f}s). Please use a shorter clip."
        )
    if duration < constants.AUDIO_MIN_DURATION_SECONDS:
        raise AudioError(
            f"Audio too short ({duration:.3f}s). Minimum is 0.1 seconds."
        )


def chunk_audio(data: np.ndarray, sample_rate: int) -> list[bytes]:
    """Split audio into 1-second chunks as PCM16 bytes."""
    chunk_size = sample_rate * constants.AUDIO_CHUNK_SECONDS
    chunks = []
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        if len(chunk) > 0:
            chunks.append(chunk.tobytes())
    return chunks


def process_audio(filepath: str) -> tuple[list[bytes], int, list[str]]:
    """Full audio processing pipeline.

    Returns (chunks, sample_rate, info_messages).
    info_messages contains user-facing info about conversions performed.
    """
    info_messages = []

    # Load
    sample_rate, data, num_channels = load_wav(filepath)

    # Convert to mono
    if num_channels == 2:
        data = convert_to_mono(data, num_channels)
        info_messages.append("Stereo audio auto-converted to mono.")

    # Resample if needed
    target_rate = constants.AUDIO_SAMPLE_RATE
    if sample_rate not in (16000, 32000, 48000):
        original_rate = sample_rate
        data = resample(data, sample_rate, target_rate)
        sample_rate = target_rate
        info_messages.append(f"Audio resampled from {original_rate}Hz to {target_rate}Hz.")
    elif sample_rate != target_rate:
        # Accept 32k and 48k as-is, but use 16k for chunking math
        pass

    # Validate duration
    validate_duration(data, sample_rate)

    # Chunk
    chunks = chunk_audio(data, sample_rate)

    return chunks, sample_rate, info_messages
