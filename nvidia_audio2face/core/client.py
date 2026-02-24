"""gRPC client for NVIDIA Audio2Face-3D service."""
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

import grpc

from .. import constants

# Import nvidia_ace protobuf stubs (from vendor/)
from nvidia_ace.services.a2f_controller import v1_pb2_grpc as a2f_controller_grpc
from nvidia_ace.controller import v1_pb2 as controller_pb2
from nvidia_ace.audio import v1_pb2 as audio_pb2
from nvidia_ace.a2f import v1_pb2 as a2f_pb2
from nvidia_ace.emotion_with_timecode import v1_pb2 as emotion_pb2

logger = logging.getLogger(__name__)


@dataclass
class AnimationFrame:
    """Single frame of animation data."""
    time_code: float
    weights: dict[str, float]  # {blendshape_name: weight_value}


@dataclass
class GenerationState:
    """Thread-safe state shared between background thread and main thread."""
    status: str = "idle"  # idle, connecting, streaming, receiving, done, error
    progress: float = 0.0  # 0.0 to 1.0
    error_message: str = ""
    blendshape_names: list[str] = field(default_factory=list)
    animation_frames: list[AnimationFrame] = field(default_factory=list)


def create_cloud_channel(api_key: str, function_id: str) -> grpc.aio.Channel:
    """Create authenticated gRPC channel to NVIDIA cloud."""
    ssl_creds = grpc.ssl_channel_credentials()

    def metadata_callback(context, callback):
        callback([
            ("function-id", function_id),
            ("authorization", f"Bearer {api_key}"),
        ], None)

    auth_creds = grpc.metadata_call_credentials(metadata_callback)
    composite_creds = grpc.composite_channel_credentials(ssl_creds, auth_creds)

    return grpc.aio.secure_channel(
        constants.CLOUD_ENDPOINT,
        composite_creds,
        options=[
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ],
    )


def create_local_channel(server_url: str) -> grpc.aio.Channel:
    """Create insecure gRPC channel to local NIM server."""
    return grpc.aio.insecure_channel(
        server_url,
        options=[
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ],
    )


def _build_audio_stream_header(
    sample_rate: int,
    face_params: dict,
    emotion_params: dict,
    weight_multipliers: dict,
    weight_offsets: dict,
) -> controller_pb2.AudioStream:
    """Build the first gRPC message (AudioStreamHeader)."""
    header = controller_pb2.AudioStreamHeader(
        audio_header=audio_pb2.AudioHeader(
            samples_per_second=sample_rate,
            bits_per_sample=constants.AUDIO_BITS_PER_SAMPLE,
            channel_count=1,
            audio_format=audio_pb2.AUDIO_FORMAT_PCM,
        ),
        face_params=a2f_pb2.FaceParameters(
            float_params=face_params,
        ),
        emotion_post_processing_params=a2f_pb2.EmotionPostProcessingParameters(
            emotion_contrast=emotion_params.get("emotion_contrast", 1.0),
            live_blend_coef=emotion_params.get("live_blend_coef", 0.7),
            enable_preferred_emotion=emotion_params.get("enable_preferred_emotion", False),
            preferred_emotion_strength=emotion_params.get("preferred_emotion_strength", 0.5),
            emotion_strength=emotion_params.get("emotion_strength", 0.6),
            max_emotions=emotion_params.get("max_emotions", 3),
        ),
        blendshape_params=a2f_pb2.BlendShapeParameters(
            bs_weight_multipliers=weight_multipliers,
            bs_weight_offsets=weight_offsets,
        ),
        emotion_params=a2f_pb2.EmotionParameters(
            live_transition_time=0.0001,
        ),
    )
    return controller_pb2.AudioStream(audio_stream_header=header)


def _build_audio_chunk_message(
    audio_bytes: bytes,
    emotions: Optional[dict] = None,
    time_code: float = 0.0,
) -> controller_pb2.AudioStream:
    """Build an audio data chunk message."""
    emotion_list = []
    if emotions:
        # EmotionWithTimeCode.emotion is a map<string, float>
        emotion_list.append(
            emotion_pb2.EmotionWithTimeCode(
                time_code=time_code,
                emotion=emotions,
            )
        )

    audio_with_emotion = a2f_pb2.AudioWithEmotion(
        audio_buffer=audio_bytes,
        emotions=emotion_list,
    )
    return controller_pb2.AudioStream(audio_with_emotion=audio_with_emotion)


def _build_end_of_audio() -> controller_pb2.AudioStream:
    """Build the EndOfAudio termination message."""
    return controller_pb2.AudioStream(
        end_of_audio=controller_pb2.AudioStream.EndOfAudio()
    )


async def generate_animation(
    channel: grpc.aio.Channel,
    audio_chunks: list[bytes],
    sample_rate: int,
    face_params: dict,
    emotion_params: dict,
    weight_multipliers: dict,
    weight_offsets: dict,
    manual_emotions: Optional[dict] = None,
    state: Optional[GenerationState] = None,
) -> GenerationState:
    """Run the full generation pipeline via bidirectional gRPC streaming.

    Args:
        channel: gRPC channel (cloud or local)
        audio_chunks: List of PCM16 audio bytes (1 second each)
        sample_rate: Audio sample rate
        face_params: FaceParameters dict
        emotion_params: EmotionPostProcessingParameters dict
        weight_multipliers: Per-blendshape multipliers dict
        weight_offsets: Per-blendshape offsets dict
        manual_emotions: Optional emotion override dict
        state: GenerationState to update (created if None)

    Returns:
        GenerationState with results
    """
    if state is None:
        state = GenerationState()

    state.status = "connecting"
    state.progress = 0.0

    stub = a2f_controller_grpc.A2FControllerServiceStub(channel)

    async def _send_stream():
        """Generator that yields audio stream messages."""
        # 1. Send header
        yield _build_audio_stream_header(
            sample_rate, face_params, emotion_params,
            weight_multipliers, weight_offsets,
        )

        state.status = "streaming"
        total_chunks = len(audio_chunks)

        # 2. Send audio chunks
        for i, chunk in enumerate(audio_chunks):
            emotions = manual_emotions if i == 0 and manual_emotions else None
            yield _build_audio_chunk_message(chunk, emotions)
            state.progress = (i + 1) / total_chunks * 0.5

        # 3. Send end of audio
        yield _build_end_of_audio()

    try:
        stream = stub.ProcessAudioStream(_send_stream())

        state.status = "receiving"
        estimated_frames = len(audio_chunks) * constants.A2F_OUTPUT_FPS
        frames_received = 0

        async for response in stream:
            # Handle header
            if response.HasField("animation_data_stream_header"):
                header = response.animation_data_stream_header
                if header.HasField("skel_animation_header"):
                    state.blendshape_names = list(
                        header.skel_animation_header.blend_shapes
                    )

            # Handle animation data
            elif response.HasField("animation_data"):
                anim = response.animation_data
                if anim.HasField("skel_animation"):
                    skel = anim.skel_animation
                    # blend_shape_weights is repeated FloatArrayWithTimeCode
                    # Each entry is one frame with time_code and values[]
                    for frame_data in skel.blend_shape_weights:
                        weights = {}
                        for j, val in enumerate(frame_data.values):
                            if j < len(state.blendshape_names):
                                weights[state.blendshape_names[j]] = val
                        state.animation_frames.append(
                            AnimationFrame(
                                time_code=frame_data.time_code,
                                weights=weights,
                            )
                        )
                        frames_received += 1

                    if estimated_frames > 0:
                        state.progress = 0.5 + (frames_received / estimated_frames) * 0.5

            # Handle status
            elif response.HasField("status"):
                resp_status = response.status
                if resp_status.code == 0:  # SUCCESS
                    state.status = "done"
                    state.progress = 1.0
                elif resp_status.code == 3:  # ERROR
                    state.status = "error"
                    state.error_message = f"Server error: {resp_status.message}"

        if state.status == "receiving":
            state.status = "done"
            state.progress = 1.0

    except grpc.aio.AioRpcError as e:
        state.status = "error"
        code = e.code()
        if code == grpc.StatusCode.UNAUTHENTICATED:
            state.error_message = "Invalid API key. Get one free at build.nvidia.com"
        elif code == grpc.StatusCode.UNAVAILABLE:
            state.error_message = "Cannot connect to Audio2Face service. Check your network/server."
        elif code == grpc.StatusCode.RESOURCE_EXHAUSTED:
            state.error_message = "API credits may be exhausted. Check your NVIDIA account."
        elif code == grpc.StatusCode.DEADLINE_EXCEEDED:
            state.error_message = "Connection timed out. Check your network/server."
        else:
            state.error_message = f"gRPC error ({code.name}): {e.details()}"
        logger.error("gRPC error: %s - %s", code, e.details())
    except Exception as e:
        state.status = "error"
        state.error_message = f"Unexpected error: {e}"
        logger.exception("Unexpected error in generation")

    return state


async def health_check(channel: grpc.aio.Channel, timeout: float = 5.0) -> tuple[bool, str]:
    """Check if the Audio2Face service is reachable.

    Returns (success, message).
    """
    try:
        await asyncio.wait_for(
            channel.channel_ready(),
            timeout=timeout,
        )
        return True, "Successfully connected to Audio2Face service."
    except asyncio.TimeoutError:
        return False, f"Connection timed out after {timeout:.0f} seconds."
    except grpc.aio.AioRpcError as e:
        code = e.code()
        if code == grpc.StatusCode.UNAUTHENTICATED:
            return False, "Authentication failed. Check your API key."
        return False, f"Connection failed: {e.details()}"
    except Exception as e:
        return False, f"Connection failed: {e}"
