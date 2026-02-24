# NVIDIA Audio2Face-3D — Complete API & Integration Reference

> Compiled from official NVIDIA documentation, GitHub repositories, and developer resources.
> Covers the current gRPC microservice API, NIM cloud deployment, local SDK, and data formats.

---

## Table of Contents

1. [Ecosystem Overview](#1-ecosystem-overview)
2. [Audio2Face-3D gRPC API (Current)](#2-audio2face-3d-grpc-api-current)
3. [gRPC Message Protocol — Detailed](#3-grpc-message-protocol--detailed)
4. [FaceParameters Reference](#4-faceparameters-reference)
5. [Emotion Parameters Reference](#5-emotion-parameters-reference)
6. [BlendShape Parameters Reference](#6-blendshape-parameters-reference)
7. [52 ARKit Blendshapes (Output Format)](#7-52-arkit-blendshapes-output-format)
8. [Audio Requirements](#8-audio-requirements)
9. [NVIDIA NIM Cloud API (build.nvidia.com)](#9-nvidia-nim-cloud-api-buildnvidiacom)
10. [Self-Hosted NIM Container (Docker)](#10-self-hosted-nim-container-docker)
11. [Audio2Face Authoring Microservice](#11-audio2face-authoring-microservice)
12. [Protobuf Data Structures](#12-protobuf-data-structures)
13. [Audio2Face-3D SDK (C++/CUDA)](#13-audio2face-3d-sdk-ccuda)
14. [Open-Source Models (HuggingFace)](#14-open-source-models-huggingface)
15. [Python SDKs & Packages](#15-python-sdks--packages)
16. [Protobuf Stubs (nvidia_ace)](#16-protobuf-stubs-nvidia_ace)
17. [Status Codes & Error Handling](#17-status-codes--error-handling)
18. [Platform Integrations](#18-platform-integrations)
19. [Config YAML Format](#19-config-yaml-format)
20. [Output CSV Format](#20-output-csv-format)
21. [Key GitHub Repositories](#21-key-github-repositories)
22. [API Reference Links](#22-api-reference-links)

---

## 1. Ecosystem Overview

NVIDIA Audio2Face is part of the **NVIDIA ACE (Avatar Cloud Engine)** platform. It converts speech audio into real-time facial animation using **ARKit blendshapes** (52 facial controls).

### Product Lines

| Product | Protocol | Port | Status |
|---------|----------|------|--------|
| **Omniverse Audio2Face** (legacy) | REST API | `localhost:8011` | Discontinued (Oct 2025) |
| **Audio2Face-3D NIM Microservice** (current) | gRPC | `52000` (local) or `443` (cloud) | Active, open-sourced |
| **Audio2Face-3D SDK** (C++/CUDA) | Native C API | N/A (library) | Active, MIT license |
| **Audio2Face Authoring Microservice** | gRPC | `50051` | Active (iterative tuning) |

### Architecture

```
┌─────────────┐     gRPC (bidirectional streaming)     ┌──────────────────────┐
│  Your App   │ ←─────────────────────────────────────→ │  Audio2Face-3D NIM   │
│  (Client)   │                                         │  (Server / Cloud)    │
│             │  SEND: Audio chunks + config             │                      │
│             │  RECV: Blendshape weights + emotions     │  HuBERT → A2F → A2E │
└─────────────┘                                         └──────────────────────┘
```

### Model Architecture

Audio2Face-3D v3.0 uses a **Transformer + Diffusion** pipeline:
1. **HuBERT** encoder extracts speech features from raw audio
2. **Audio2Face** transformer generates facial motion (blendshape weights)
3. **Audio2Emotion** classifier detects emotion from speech
4. Combined output: 52 blendshape weights + 10 emotion values per frame at 30 FPS

Parameters: ~180 million (1.80 × 10^8)

---

## 2. Audio2Face-3D gRPC API (Current)

### Service Definition

```protobuf
service A2FControllerService {
    rpc ProcessAudioStream(stream AudioStream) returns (stream AnimationDataStream);
}
```

- **Package**: `nvidia_ace.services.a2f_controller.v1`
- **Type**: Bidirectional streaming (client streams audio, server streams animation)
- **Single RPC**: `ProcessAudioStream` is the only call needed

### Communication Pattern

```
Client                              Server
  │                                   │
  │──── AudioStreamHeader ──────────→ │  (1st message: config + audio format)
  │──── AudioWithEmotion ───────────→ │  (2nd..Nth: audio chunks)
  │──── AudioWithEmotion ───────────→ │
  │──── ...                           │
  │──── EndOfAudio ─────────────────→ │  (final: signals end of input)
  │                                   │
  │←── AnimationDataStreamHeader ──── │  (1st response: blendshape names)
  │←── AnimationData ──────────────── │  (2nd..Mth: weights per frame)
  │←── AnimationData ──────────────── │
  │←── ...                            │
  │←── Status ─────────────────────── │  (final: success/error)
  │                                   │
```

### Legacy Unidirectional Mode (Backwards Compatibility)

Two separate services exist for push/pull streaming:

```protobuf
// Push audio to server
service A2FService {
    rpc PushAudioStream(stream AudioStream) returns (Status);
}

// Pull animation from server
service AnimationDataService {
    rpc PushAnimationDataStream(stream AnimationDataStream) returns (Status);
    rpc PullAnimationDataStream(AnimationIds) returns (stream AnimationDataStream);
}
```

- **Package**: `nvidia_ace.services.a2f.v1` and `nvidia_ace.services.animation_data.v1`
- Use **bidirectional mode** (`A2FControllerService`) for new integrations

---

## 3. gRPC Message Protocol — Detailed

### 3.1 Input: AudioStream (Client → Server)

The client sends three types of messages in sequence:

#### Message 1: AudioStreamHeader (REQUIRED, exactly once, FIRST)

```python
AudioStream(
    audio_stream_header=AudioStreamHeader(
        audio_header=AudioHeader(
            samples_per_second=16000,        # 16kHz recommended
            bits_per_sample=16,              # Always 16-bit PCM
            channel_count=1,                 # Mono only
            audio_format=AUDIO_FORMAT_PCM    # Only PCM supported
        ),
        face_params=FaceParameters(
            float_params={
                "upperFaceStrength": 1.0,
                "upperFaceSmoothing": 0.001,
                "lowerFaceStrength": 1.2,
                "lowerFaceSmoothing": 0.006,
                "faceMaskLevel": 0.6,
                "faceMaskSoftness": 0.0085,
                "skinStrength": 1.0,
                "eyelidOpenOffset": 0.06,
                "lipOpenOffset": -0.02,
            }
        ),
        emotion_post_processing_params=EmotionPostProcessingParameters(
            emotion_contrast=1.0,
            live_blend_coef=0.7,
            enable_preferred_emotion=False,
            preferred_emotion_strength=0.5,
            emotion_strength=0.6,
            max_emotions=3
        ),
        blendshape_params=BlendShapeParameters(
            bs_weight_multipliers={             # Per-blendshape scaling
                "EyeBlinkLeft": 1.0,
                "JawOpen": 1.0,
                "MouthSmileLeft": 1.2,          # Example: boost smiles
                # ... all 52 entries
            },
            bs_weight_offsets={                  # Per-blendshape offset
                "EyeBlinkLeft": 0.0,
                # ... all 52 entries, usually 0.0
            },
            enable_clamping_bs_weight=False
        ),
        emotion_params=EmotionParameters(
            live_transition_time=0.0001,
            beginning_emotion={
                "amazement": 0.0,
                "anger": 0.0,
                "cheekiness": 0.0,
                "disgust": 0.0,
                "fear": 0.0,
                "grief": 0.0,
                "joy": 0.0,
                "outofbreath": 0.0,
                "pain": 0.0,
                "sadness": 0.0
            }
        )
    )
)
```

#### Message 2..N: AudioWithEmotion (one or more data chunks)

```python
AudioStream(
    audio_with_emotion=AudioWithEmotion(
        audio_buffer=b"<1 second of PCM16 mono bytes>",  # = 32000 bytes at 16kHz
        # First chunk can include emotion timecodes:
        emotions=[
            EmotionWithTimeCode(
                emotion=Emotion(
                    amazement=0.0,
                    anger=0.0,
                    cheekiness=0.0,
                    disgust=0.0,
                    fear=0.0,
                    grief=0.0,
                    joy=0.5,        # Example: set initial joy
                    outofbreath=0.0,
                    pain=0.0,
                    sadness=0.0
                ),
                time_code=0.0       # Seconds from start
            )
        ]
    )
)
```

**Chunk size**: 1 second of audio per message = `sample_rate` samples = `sample_rate * 2` bytes (16-bit).
At 16kHz: each chunk = 16000 samples = 32000 bytes.

#### Message N+1: EndOfAudio (REQUIRED, exactly once, LAST)

```python
AudioStream(end_of_audio=EndOfAudio())
```

The server only returns a final gRPC status after receiving this message.

### 3.2 Output: AnimationDataStream (Server → Client)

#### Message 1: AnimationDataStreamHeader

```python
AnimationDataStream(
    animation_data_stream_header=AnimationDataStreamHeader(
        skel_animation_header=SkelAnimationHeader(
            blend_shapes=[                      # Ordered list of 52 names
                "EyeBlinkLeft",
                "EyeLookDownLeft",
                "EyeLookInLeft",
                # ... all 52
            ]
        ),
        audio_header=AudioHeader(
            samples_per_second=16000,
            bits_per_sample=16,
            channel_count=1,
            audio_format=AUDIO_FORMAT_PCM
        ),
        start_time_code_since_epoch=1708876543.123  # Unix timestamp
    )
)
```

#### Message 2..M: AnimationData (frame batches)

```python
AnimationDataStream(
    animation_data=AnimationData(
        skel_animation=SkelAnimation(
            blend_shape_weights=FloatArrayWithTimeCode(
                time_code=0.0,                  # Seconds from start
                values=[0.0, 0.0, 0.0, ...]    # 52 floats (0.0-1.0)
            )
            # Multiple entries per message (batched):
            # time_code=0.033, values=[...]
            # time_code=0.066, values=[...]
        ),
        audio=AudioWithTimeCode(
            audio_buffer=b"<processed audio bytes>",
            time_code=0.0
        ),
        metadata={
            "emotion_aggregate": "<serialized EmotionAggregate>"
        }
    )
)
```

**Frame rate**: Exactly 30 FPS (timecodes: 0.0, 0.0333, 0.0666, 0.1, ...)

#### Message M+1: Status (final)

```python
AnimationDataStream(
    status=Status(
        code=0,            # 0=SUCCESS, 1=INFO, 2=WARNING, 3=ERROR
        message="SUCCESS"
    )
)
```

---

## 4. FaceParameters Reference

All face parameters are passed as `float_params` dict in `FaceParameters`:

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `upperFaceStrength` | float | 0.0–2.0 | 1.0 | Intensity of upper face motion (brows, forehead) |
| `lowerFaceStrength` | float | 0.0–2.0 | 1.2 | Intensity of lower face motion (jaw, lips, mouth) |
| `skinStrength` | float | 0.0–2.0 | 1.0 | Overall skin motion range |
| `upperFaceSmoothing` | float | 0.0–0.1 | 0.001 | Temporal smoothing for upper face |
| `lowerFaceSmoothing` | float | 0.0–0.1 | 0.006 | Temporal smoothing for lower face |
| `faceMaskLevel` | float | 0.0–1.0 | 0.6 | Boundary determination between upper/lower face regions |
| `faceMaskSoftness` | float | 0.001–0.5 | 0.0085 | Softness of the mask boundary blend |
| `eyelidOpenOffset` | float | -1.0–1.0 | 0.06 | Base eyelid position offset |
| `lipOpenOffset` | float | -0.02–0.2 | -0.02 | Base lip opening offset |
| `blinkStrength` | float | — | — | Blink intensity multiplier |
| `blinkOffset` | float | — | — | Blink position offset |
| `tongueStrength` | float | — | — | Tongue animation intensity |
| `tongueHeightOffset` | float | — | — | Tongue vertical offset |
| `tongueDepthOffset` | float | — | — | Tongue depth offset |

### Per-Model Default Overrides

**James v2.3** (recommended defaults):
```python
{
    "upperFaceStrength": 1.0,
    "lowerFaceStrength": 1.2,       # Slightly boosted
    "skinStrength": 1.0,
    "upperFaceSmoothing": 0.001,
    "lowerFaceSmoothing": 0.006,
    "faceMaskLevel": 0.6,
    "faceMaskSoftness": 0.0085,
    "eyelidOpenOffset": 0.06,
    "lipOpenOffset": -0.02,
}
```

**Claire v2.3**: Same defaults, optimized for Chinese + English female voice.

**Mark v2.3**: Same defaults, high-resolution geometry mode.

---

## 5. Emotion Parameters Reference

### EmotionPostProcessingParameters

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `emotion_contrast` | float | 0.3–3.0 | 1.0 | How distinct emotions appear (higher = more separation) |
| `live_blend_coef` | float | 0.0–1.0 | 0.7 | Blending factor for live emotion transitions |
| `enable_preferred_emotion` | bool | — | False | Enable preferred emotion bias |
| `preferred_emotion_strength` | float | 0.0–1.0 | 0.5 | How strongly preferred emotion is weighted |
| `emotion_strength` | float | 0.0–1.0 | 0.6 | Overall emotion strength in output |
| `max_emotions` | int | 1–6 | 3 | Maximum simultaneous active emotions |

### Emotion Names (10 total)

All emotion values range 0.0–1.0:

| Name | Description |
|------|-------------|
| `amazement` | Surprise, wonder |
| `anger` | Anger, frustration |
| `cheekiness` | Playful, mischievous |
| `disgust` | Revulsion |
| `fear` | Fear, anxiety |
| `grief` | Deep sadness |
| `joy` | Happiness, smile |
| `outofbreath` | Panting, breathlessness |
| `pain` | Physical pain |
| `sadness` | Mild sadness |

### EmotionParameters (Stream Header)

| Parameter | Type | Description |
|-----------|------|-------------|
| `live_transition_time` | float | Transition speed between emotion states (seconds) |
| `beginning_emotion` | dict | Initial emotion state at stream start (10 emotion values) |

### EmotionWithTimeCode (Per-Chunk)

Sent with audio chunks to override emotion at specific timecodes:

```python
EmotionWithTimeCode(
    emotion=Emotion(joy=0.8, sadness=0.0, ...),
    time_code=2.5  # Override emotion at 2.5 seconds
)
```

---

## 6. BlendShape Parameters Reference

### BlendShapeParameters

| Field | Type | Description |
|-------|------|-------------|
| `bs_weight_multipliers` | dict[str, float] | Per-blendshape scaling factor (1.0 = default) |
| `bs_weight_offsets` | dict[str, float] | Per-blendshape constant offset (0.0 = default) |
| `enable_clamping_bs_weight` | bool | Clamp output weights to [0.0, 1.0] range |

### Default Multipliers (James v2.3)

Special values (non-1.0):

```python
# Zeroed (not animated by model):
"EyeLookDownLeft": 0.0,
"EyeLookInLeft": 0.0,
"EyeLookOutLeft": 0.0,
"EyeLookUpLeft": 0.0,
"EyeLookDownRight": 0.0,
"EyeLookInRight": 0.0,
"EyeLookOutRight": 0.0,
"EyeLookUpRight": 0.0,
"TongueOut": 0.0,

# Reduced:
"JawLeft": 0.2,
"JawRight": 0.2,
"MouthLeft": 0.2,
"MouthRight": 0.2,
"MouthStretchLeft": 0.05,
"MouthStretchRight": 0.05,
"CheekPuff": 0.2,

# Boosted:
"MouthSmileLeft": 1.2,
"MouthSmileRight": 1.2,
"BrowDownLeft": 1.2,
"BrowDownRight": 1.2,
"BrowInnerUp": 1.3,
```

All others default to 1.0. All offsets default to 0.0.

---

## 7. 52 ARKit Blendshapes (Output Format)

The server returns weights in this exact order (matching NVIDIA config files):

```
Index  Name                    Index  Name
─────  ──────────────────────  ─────  ──────────────────────
  0    EyeBlinkLeft              26   MouthFrownLeft
  1    EyeLookDownLeft           27   MouthFrownRight
  2    EyeLookInLeft             28   MouthDimpleLeft
  3    EyeLookOutLeft            29   MouthDimpleRight
  4    EyeLookUpLeft             30   MouthStretchLeft
  5    EyeSquintLeft             31   MouthStretchRight
  6    EyeWideLeft               32   MouthRollLower
  7    EyeBlinkRight             33   MouthRollUpper
  8    EyeLookDownRight          34   MouthShrugLower
  9    EyeLookInRight            35   MouthShrugUpper
 10    EyeLookOutRight           36   MouthPressLeft
 11    EyeLookUpRight            37   MouthPressRight
 12    EyeSquintRight            38   MouthLowerDownLeft
 13    EyeWideRight              39   MouthLowerDownRight
 14    JawForward                40   MouthUpperUpLeft
 15    JawLeft                   41   MouthUpperUpRight
 16    JawRight                  42   BrowDownLeft
 17    JawOpen                   43   BrowDownRight
 18    MouthClose                44   BrowInnerUp
 19    MouthFunnel               45   BrowOuterUpLeft
 20    MouthPucker               46   BrowOuterUpRight
 21    MouthLeft                 47   CheekPuff
 22    MouthRight                48   CheekSquintLeft
 23    MouthSmileLeft            49   CheekSquintRight
 24    MouthSmileRight           50   NoseSneerLeft
 25    MouthFrownLeft            51   NoseSneerRight
                                (52   TongueOut — always 0 unless tongue model)
```

### Important Deviations from Standard ARKit

| Blendshape | Standard ARKit | NVIDIA A2F Behavior |
|------------|---------------|---------------------|
| `MouthClose` | Lips close together | **Includes jaw opening** (deviates from Apple spec) |
| `EyeLookDown/In/Out/Up` | Eye gaze direction | **Always 0** (not animated) |
| `TongueOut` | Tongue protrusion | **Always 0** unless tongue model enabled |

### Not Animated (always output 0.0)

- All `EyeLook*` directions (8 shapes): indices 1-4, 8-11
- `TongueOut`: index 52 (unless tongue-enabled model variant)
- Head rotation (HeadRoll/Pitch/Yaw): not part of 52 ARKit set

---

## 8. Audio Requirements

### Input Format

| Property | Requirement | Notes |
|----------|-------------|-------|
| **Format** | WAV, PCM | Only `AUDIO_FORMAT_PCM` supported |
| **Bit depth** | 16-bit | `bits_per_sample = 16` |
| **Channels** | Mono (1) | Stereo must be downmixed before sending |
| **Sample rate** | 16 kHz recommended | 32kHz, 48kHz also accepted; others need resampling |
| **Max buffer** | 10 seconds per gRPC message | Chunk longer audio into 1-second pieces |
| **Max duration** | 300 seconds (5 minutes) | Per audio clip |
| **Min duration** | ~0.1 seconds | Very short clips may produce poor results |

### Resampling Strategy (without scipy)

```python
import numpy as np

def resample_linear(data: np.ndarray, original_rate: int, target_rate: int = 16000) -> np.ndarray:
    """Resample audio using linear interpolation (numpy only)."""
    if original_rate == target_rate:
        return data
    ratio = target_rate / original_rate
    new_length = int(len(data) * ratio)
    x_old = np.linspace(0, 1, len(data))
    x_new = np.linspace(0, 1, new_length)
    return np.interp(x_new, x_old, data.astype(np.float64)).astype(np.int16)
```

### Stereo to Mono Conversion

```python
def stereo_to_mono(data: np.ndarray) -> np.ndarray:
    """Average left and right channels."""
    left = data[0::2].astype(np.int32)
    right = data[1::2].astype(np.int32)
    return ((left + right) // 2).astype(np.int16)
```

### Chunking Strategy

```python
def chunk_audio(data: np.ndarray, sample_rate: int, chunk_seconds: int = 1) -> list[bytes]:
    """Split audio into 1-second chunks as PCM16 bytes."""
    chunk_size = sample_rate * chunk_seconds
    chunks = []
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        if len(chunk) > 0:
            chunks.append(chunk.tobytes())
    return chunks
```

### Output Rate

- **30 frames per second** of audio processed
- Timecodes: 0.0, 0.0333, 0.0666, 0.1, ... (1/30 second intervals)
- 10 seconds of audio → 300 animation frames

---

## 9. NVIDIA NIM Cloud API (build.nvidia.com)

### Endpoint

| Property | Value |
|----------|-------|
| **URL** | `grpc.nvcf.nvidia.com:443` |
| **Protocol** | gRPC over HTTPS (TLS) |
| **Auth** | Bearer token + Function ID in metadata |

### Authentication

```python
import grpc

def create_cloud_channel(api_key: str, function_id: str):
    """Create authenticated gRPC channel to NVIDIA cloud."""
    # SSL credentials for TLS
    ssl_creds = grpc.ssl_channel_credentials()

    # Metadata credentials (sent with every RPC)
    def metadata_callback(context, callback):
        callback([
            ("function-id", function_id),
            ("authorization", f"Bearer {api_key}"),
        ], None)

    auth_creds = grpc.metadata_call_credentials(metadata_callback)

    # Combine SSL + auth
    composite_creds = grpc.composite_channel_credentials(ssl_creds, auth_creds)

    # Create async channel
    channel = grpc.aio.secure_channel("grpc.nvcf.nvidia.com:443", composite_creds)
    return channel
```

### Available Models and Function IDs

| Model | Tongue | Function ID |
|-------|--------|-------------|
| **Mark v2.3** | Yes | `8efc55f5-6f00-424e-afe9-26212cd2c630` |
| Mark v2.3 | No | `cf145b84-423b-4222-bfdd-15bb0142b0fd` |
| **Claire v2.3** | Yes | `0961a6da-fb9e-4f2e-8491-247e5fd7bf8d` |
| Claire v2.3 | No | `617f80a7-85e4-4bf0-9dd6-dcb61e886142` |
| **James v2.3** | Yes | `9327c39f-a361-4e02-bd72-e11b4c9b7b5e` |
| James v2.3 | No | `8082bdcb-9968-4dc5-8705-423ea98b8fc2` |

### Getting an API Key

1. Go to https://build.nvidia.com/nvidia/audio2face-3d
2. Click "Get API Key" (sign in with NVIDIA account)
3. Copy the key (format: `nvapi-...`)
4. Free tier: 1,000+ inference credits

### Cloud Client Usage (CLI)

```bash
python ./nim_a2f_3d_client.py <audio.wav> config.yml \
  --apikey <API_KEY> \
  --function-id <FUNCTION_ID>
```

---

## 10. Self-Hosted NIM Container (Docker)

### Prerequisites

- **NVIDIA AI Enterprise** subscription or evaluation license
- NGC API Key (from `org.ngc.nvidia.com/setup/api-keys`)
- Docker with NVIDIA Container Toolkit (`nvidia-docker`)
- Supported GPUs: A10G, A30, A100, H100, L4, L40S, RTX 6000, RTX 4090, RTX 50 Series

### Launch Command

```bash
export NGC_API_KEY=<your_key>
echo "$NGC_API_KEY" | docker login nvcr.io --username '$oauthtoken' --password-stdin

docker run -it --rm --name audio2face-3d \
  --gpus all \
  --network=host \
  -e NGC_API_KEY=$NGC_API_KEY \
  -e NIM_MANIFEST_PROFILE=<profile_id> \
  -e PERF_A2F_MODEL=mark_v2.3 \
  nvcr.io/nim/nvidia/audio2face-3d:1.3.16
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NGC_API_KEY` | Authentication token from NGC | Yes |
| `NIM_MANIFEST_PROFILE` | GPU-specific optimization profile ID | Yes |
| `PERF_A2F_MODEL` | Model selection: `james_v2.3`, `claire_v2.3`, `mark_v2.3` | No (default varies) |
| `NIM_RELAX_MEM_CONSTRAINTS` | Memory optimization flag | No |
| `NIM_DISABLE_MODEL_DOWNLOAD` | Skip NGC model download (use local cache) | No |
| `LOCAL_NIM_CACHE` | Path to local model storage | No |

### Default Ports

- **gRPC**: `52000`
- **Health**: same port

### Local Channel Creation

```python
import grpc

def create_local_channel(server_url: str = "localhost:52000"):
    """Create insecure gRPC channel to local NIM server."""
    channel = grpc.aio.insecure_channel(server_url)
    return channel
```

### Health Check

```bash
python3 a2f_3d.py health_check --url 0.0.0.0:52000
```

### Run Inference

```bash
python3 a2f_3d.py run_inference audio.wav config_mark_v2.yml -u 127.0.0.1:52000
```

Output files generated:
- `animation_frames.csv` — blendshape weights per frame
- `out.wav` — processed/echo audio for sync verification
- `a2f_3d_input_emotions.csv` — input emotion parameters sent
- `a2f_3d_smoothed_emotion_output.csv` — smoothed emotion outputs received

---

## 11. Audio2Face Authoring Microservice

A companion microservice for iterative parameter tuning without re-processing audio.

### gRPC Services

| Service | RPC | Description |
|---------|-----|-------------|
| `A2FAuthoringService` | `UploadAudioClip` | Process audio, return hash + blendshape key list |
| `A2FAuthoringService` | `GetAvatarFacePose` | Get animation frame at specific timecode |

### Configuration

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `endpoint` | `0.0.0.0:50051` | — | gRPC listening address |
| `a2e_batch_size` | 10 | 1–256 | Emotion processing batch size |
| `a2f_batch_size` | 10 | 1–256 | Face animation batch size |
| `clip_db_ttl` | 3600 | seconds | Audio cache retention |
| `clip_db_max_size` | 10 GB | — | Max audio storage |

### Supported Avatars

- Mark v2.2
- Claire v1.3

### PyPI Package

```bash
pip install nvidia-audio2face-3d-authoring
```

---

## 12. Protobuf Data Structures

### Core Message Hierarchy

```
AnimationDataStreamHeader
├── request_id: string
├── stream_id: string
├── target_object_id: string
├── source_service_id: string
├── audio_header: AudioHeader
├── skel_animation_header: SkelAnimationHeader
│   ├── blend_shapes: repeated string    ← 52 ARKit names
│   └── joints: repeated string
├── start_time_code_since_epoch: double
└── metadata: map<string, string>

AnimationData
├── skel_animation: SkelAnimation
│   ├── blend_shape_weights: FloatArrayWithTimeCode
│   │   ├── time_code: double            ← seconds from start
│   │   └── values: repeated float       ← 52 weights
│   ├── translations: Float3ArrayWithTimeCode
│   ├── rotations: QuatFArrayWithTimeCode
│   └── scales: Float3ArrayWithTimeCode
├── audio: AudioWithTimeCode
│   ├── audio_buffer: bytes
│   └── time_code: double
├── camera: Camera
└── metadata: map<string, string>
```

### Primitive Types

```protobuf
message QuatF {
    float real = 1;  // w
    float i = 2;     // x
    float j = 3;     // y
    float k = 4;     // z
}

message Float3 {
    float x = 1;
    float y = 2;
    float z = 3;
}

message FloatWithTimeCode {
    double time_code = 1;
    float value = 2;
}

message FloatArrayWithTimeCode {
    double time_code = 1;
    repeated float values = 2;
}

message Float3WithTimeCode {
    double time_code = 1;
    Float3 value = 2;
}

message QuatFWithTimeCode {
    double time_code = 1;
    QuatF value = 2;
}
```

### AudioHeader

```protobuf
message AudioHeader {
    uint32 samples_per_second = 1;   // 16000
    uint32 bits_per_sample = 2;      // 16
    uint32 channel_count = 3;        // 1 (mono)
    AudioFormat audio_format = 4;    // AUDIO_FORMAT_PCM
}

enum AudioFormat {
    AUDIO_FORMAT_PCM = 0;
    // Only PCM is supported
}
```

### Coordinate System

- **Y-axis**: Up
- **X-axis**: Left (from avatar's perspective)
- **Z-axis**: Forward

---

## 13. Audio2Face-3D SDK (C++/CUDA)

### Overview

Local, GPU-accelerated facial animation without network dependency.

- **Repository**: https://github.com/NVIDIA/Audio2Face-3D-SDK
- **License**: MIT
- **Performance**: Faster than 60 FPS frame generation
- **Multi-track**: Process multiple simultaneous audio streams

### System Requirements

| Requirement | Minimum |
|-------------|---------|
| **GPU** | NVIDIA RTX 30xx, 40xx, or 50xx |
| **VRAM** | 4 GB+ |
| **RAM** | 8 GB+ |
| **Storage** | 10 GB+ |
| **CUDA** | >= 12.8, < 13.0 (12.9 recommended) |
| **TensorRT** | >= 10.13, < 11.0 |
| **Python** | >= 3.8, <= 3.10.x |
| **OS** | Windows 10/11 or Linux (Ubuntu 20.04+) |

### Build (Windows)

```bash
git clone https://github.com/NVIDIA/Audio2Face-3D-SDK.git
cd Audio2Face-3D-SDK
git lfs pull
.\fetch_deps.bat release
set TENSORRT_ROOT_DIR=C:\path\to\tensorrt
.\build.bat all release
```

### Build Output

```
_build/release/
├── audio2emotion-sdk/
│   ├── bin/     (samples, tests)
│   └── lib/     (static libraries)
├── audio2face-sdk/
│   ├── bin/     (samples, tests)
│   └── lib/     (static libraries)
├── audio2x-common/
│   └── ...      (common utilities)
└── audio2x-sdk/
    ├── bin/     (audio2x.dll / libaudio2x.so — the unified library)
    ├── include/ (C header files for ctypes)
    └── lib/     (import libraries)
```

### Key Library File

- **Windows**: `audio2x-sdk/bin/audio2x.dll`
- **Linux**: `audio2x-sdk/bin/libaudio2x.so`
- **Interface**: C API (can be called via Python `ctypes`)

### Model Download

Models are gated on HuggingFace. Steps:
1. Accept license at https://huggingface.co/nvidia/Audio2Emotion-v2.2
2. Generate HuggingFace token with gated repo read access
3. Run `hf auth login`
4. Run `./download_models.bat` (Windows) or `./download_models.sh` (Linux)
5. Convert to TensorRT: `./gen_testdata.bat`

---

## 14. Open-Source Models (HuggingFace)

### Audio2Face-3D v3.0 (Latest — Diffusion)

| Property | Value |
|----------|-------|
| **Architecture** | Transformer + Diffusion (HuBERT-based) |
| **Parameters** | 1.80 × 10^8 |
| **Input** | Float array (1D), 16kHz mono audio |
| **Output** | Float array (2D) — skin, tongue, jaw, eyeball motion |
| **License** | NVIDIA Open Model License |
| **URL** | https://huggingface.co/nvidia/Audio2Face-3D-v3.0 |

### Audio2Face-3D v2.3.1 (Regression)

Three character-specific models:

| Model | HuggingFace URL |
|-------|-----------------|
| James | `nvidia/Audio2Face-3D-v2.3.1-James` |
| Claire | `nvidia/Audio2Face-3D-v2.3.1-Claire` |
| Mark | `nvidia/Audio2Face-3D-v2.3.1-Mark` |

### Audio2Emotion

| Version | Description |
|---------|-------------|
| v3.0 | Latest emotion classifier (experimental) |
| v2.2 | Stable emotion classifier: anger, disgust, fear, joy, neutral, sadness |

---

## 15. Python SDKs & Packages

### Official: nvidia-audio2face-3d (PyPI)

```bash
pip install nvidia-audio2face-3d
```

- **Version**: 1.3.0 (April 2025)
- **Python**: >= 3.8
- Provides gRPC protobuf stubs and services for Audio2Face-3D NIM
- Dependencies: grpcio, protobuf

### Official: nvidia_ace wheels (from Samples repo)

```bash
pip install nvidia_ace-1.2.0-py3-none-any.whl
```

From the `Audio2Face-3D-Samples` repository. Used by sample applications.

### Community: py_audio2face

```bash
pip install py_audio2face
pip install py_audio2face[streaming]   # includes gRPC support
```

- **License**: GPL-3.0
- **Note**: Wraps the legacy Omniverse REST API — may not work with NIM microservice

```python
import py_audio2face as pya2f

a2f = pya2f.Audio2Face()

# Single file
a2f.audio2face_single(
    audio_file_path="audio.wav",
    output_path="animation.usd",
    fps=60,
    emotion_auto_detect=True
)

# Batch
a2f.audio2face_folder(input_folder="wavs/", output_folder="output/", fps=60)

# Manual emotion
a2f.set_emotion(anger=0.9, disgust=0.5, update_settings=True)
```

---

## 16. Protobuf Stubs (nvidia_ace)

### Source

The Maya-ACE repository ships pre-compiled Python protobuf stubs:
**Repository**: https://github.com/NVIDIA/Maya-ACE
**Path**: `python/grpc_py/nvidia_ace/`
**License**: MIT

### File Structure

```
nvidia_ace/
├── __init__.py
├── a2f/
│   └── v1_pb2.py                            # AudioWithEmotion, FaceParameters, BlendShapeParameters
├── audio/
│   └── v1_pb2.py                            # AudioHeader, AudioFormat
├── controller/
│   └── v1_pb2.py                            # AudioStream, AudioStreamHeader
├── animation_data/
│   └── v1_pb2.py                            # AnimationData, AnimationDataStreamHeader
├── animation_id/
│   └── v1_pb2.py                            # AnimationIds
├── emotion_with_timecode/
│   └── v1_pb2.py                            # EmotionWithTimeCode, Emotion
├── emotion_aggregate/
│   └── v1_pb2.py                            # EmotionAggregate
├── status/
│   └── v1_pb2.py                            # Status
├── services/
│   └── a2f_controller/
│       └── v1_pb2_grpc.py                   # A2FControllerServiceStub
└── health/
    └── v1_pb2_grpc.py                       # HealthStub (for health checks)
```

### Usage in Addon

```python
# Add vendor/ to sys.path at register time:
import sys, os
vendor_path = os.path.join(os.path.dirname(__file__), "vendor")
if vendor_path not in sys.path:
    sys.path.insert(0, vendor_path)

# Then import normally:
from nvidia_ace.services.a2f_controller import v1_pb2_grpc
from nvidia_ace.controller import v1_pb2 as controller_pb2
from nvidia_ace.audio import v1_pb2 as audio_pb2
from nvidia_ace.a2f import v1_pb2 as a2f_pb2
from nvidia_ace.animation_data import v1_pb2 as animation_pb2
from nvidia_ace.emotion_with_timecode import v1_pb2 as emotion_pb2
from nvidia_ace.status import v1_pb2 as status_pb2
```

---

## 17. Status Codes & Error Handling

### Animation Status Codes

| Code | Name | Description |
|------|------|-------------|
| 0 | SUCCESS | Processing completed successfully |
| 1 | INFO | Informational message |
| 2 | WARNING | Non-fatal issue |
| 3 | ERROR | Processing failed |

### Common gRPC Error Codes

| gRPC Code | Constant | Typical Cause | User Message |
|-----------|----------|---------------|--------------|
| 0 | OK | Success | — |
| 2 | UNKNOWN | Server internal error | "Server error. Try again." |
| 4 | DEADLINE_EXCEEDED | Timeout | "Connection timed out." |
| 7 | PERMISSION_DENIED | Wrong API key | "Invalid API key." |
| 8 | RESOURCE_EXHAUSTED | Rate limit / no credits | "API credits exhausted." |
| 13 | INTERNAL | Server crash | "Server error. Try again." |
| 14 | UNAVAILABLE | Server down / network issue | "Cannot connect to server." |
| 16 | UNAUTHENTICATED | Missing/invalid auth | "No API key configured." |

### Error Handling Pattern

```python
import grpc

try:
    async for response in stream:
        # Process response
        pass
except grpc.aio.AioRpcError as e:
    code = e.code()
    if code == grpc.StatusCode.UNAUTHENTICATED:
        error = "Invalid API key. Get one at build.nvidia.com"
    elif code == grpc.StatusCode.UNAVAILABLE:
        error = "Cannot connect to Audio2Face service. Check network."
    elif code == grpc.StatusCode.RESOURCE_EXHAUSTED:
        error = "API credits exhausted. Check your NVIDIA account."
    elif code == grpc.StatusCode.DEADLINE_EXCEEDED:
        error = "Connection timed out after 10 seconds."
    else:
        error = f"gRPC error ({code.name}): {e.details()}"
```

---

## 18. Platform Integrations

### Existing Official Plugins

| Platform | Repository | License | Status |
|----------|-----------|---------|--------|
| **Maya** | [NVIDIA/Maya-ACE](https://github.com/NVIDIA/Maya-ACE) v2.0 | MIT | Active |
| **Unreal Engine 5** | NVIDIA ACE Plugin v2.5 | — | Active (UE 5.5, 5.6) |
| **Blender** (legacy) | [NVIDIA-Omniverse/blender_omniverse_addons](https://github.com/NVIDIA-Omniverse/blender_omniverse_addons) v4.2.0 | — | USD export/import only |

### Maya-ACE Architecture (Reference for our Blender addon)

The Maya-ACE plugin is the best reference implementation:
- Uses same nvidia_ace protobuf stubs
- Same gRPC bidirectional streaming pattern
- Local + remote inference support
- Real-time viewport preview
- FBX export of blendshape animation

### Training Framework

- **Repository**: https://github.com/NVIDIA/Audio2Face-3D-Training-Framework
- Custom model creation from proprietary datasets
- Multi-language support
- Standardized JSON model card export

---

## 19. Config YAML Format

NVIDIA's sample applications use YAML config files. Our addon stores these as Python dicts instead.

### Example: config_james_v2.yml

```yaml
audio_header:
  samples_per_second: 16000
  bits_per_sample: 16
  channel_count: 1
  audio_format: AUDIO_FORMAT_PCM

face_params:
  float_params:
    upperFaceStrength: 1.0
    upperFaceSmoothing: 0.001
    lowerFaceStrength: 1.2
    lowerFaceSmoothing: 0.006
    faceMaskLevel: 0.6
    faceMaskSoftness: 0.0085
    skinStrength: 1.0
    eyelidOpenOffset: 0.06
    lipOpenOffset: -0.02

emotion_post_processing_params:
  emotion_contrast: 1.0
  live_blend_coef: 0.7
  enable_preferred_emotion: false
  preferred_emotion_strength: 0.5
  emotion_strength: 0.6
  max_emotions: 3

blendshape_params:
  bs_weight_multipliers:
    EyeBlinkLeft: 1.0
    EyeLookDownLeft: 0.0
    # ... all 52
  bs_weight_offsets:
    EyeBlinkLeft: 0.0
    # ... all 52
  enable_clamping_bs_weight: false

emotion_params:
  live_transition_time: 0.0001
  beginning_emotion:
    amazement: 0.0
    anger: 0.0
    cheekiness: 0.0
    disgust: 0.0
    fear: 0.0
    grief: 0.0
    joy: 0.0
    outofbreath: 0.0
    pain: 0.0
    sadness: 0.0
```

---

## 20. Output CSV Format

NVIDIA's tools export animation data as CSV:

### animation_frames.csv

```csv
timeCode,blendShapes.EyeBlinkLeft,blendShapes.EyeLookDownLeft,...,blendShapes.NoseSneerRight
0.0,0.0,0.0,...,0.0
0.033333,0.01,0.0,...,0.0
0.066667,0.03,0.0,...,0.001
...
```

- One row per frame (30 rows per second)
- Columns: `timeCode` + 52 blendshape columns prefixed with `blendShapes.`
- Values: floats, typically 0.0–1.0

### emotion_output.csv

```csv
timeCode,amazement,anger,cheekiness,disgust,fear,grief,joy,outofbreath,pain,sadness
0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.12,0.0,0.0,0.0
0.033333,0.0,0.0,0.0,0.0,0.0,0.0,0.15,0.0,0.0,0.0
...
```

---

## 21. Key GitHub Repositories

| Repository | Description | License |
|------------|-------------|---------|
| [NVIDIA/Audio2Face-3D](https://github.com/NVIDIA/Audio2Face-3D) | Main collection/hub repo | Various |
| [NVIDIA/Audio2Face-3D-Samples](https://github.com/NVIDIA/Audio2Face-3D-Samples) | gRPC sample apps, proto files, configs | Apache 2.0 |
| [NVIDIA/Audio2Face-3D-SDK](https://github.com/NVIDIA/Audio2Face-3D-SDK) | C++/CUDA local SDK | MIT |
| [NVIDIA/Audio2Face-3D-Training-Framework](https://github.com/NVIDIA/Audio2Face-3D-Training-Framework) | Custom model training | Apache 2.0 |
| [NVIDIA/Maya-ACE](https://github.com/NVIDIA/Maya-ACE) | Maya plugin (reference impl) | MIT |
| [NVIDIA/ACE](https://github.com/NVIDIA/ACE) | ACE samples and workflows | Various |
| [NVIDIA-Omniverse/blender_omniverse_addons](https://github.com/NVIDIA-Omniverse/blender_omniverse_addons) | Blender USD addons (legacy) | — |
| [SocAIty/py_audio2face](https://github.com/SocAIty/py_audio2face) | Community Python wrapper | GPL-3.0 |

---

## 22. API Reference Links

### Official Documentation
- **Microservice docs**: https://docs.nvidia.com/ace/audio2face-3d-microservice/latest/
- **gRPC API**: https://docs.nvidia.com/ace/audio2face-3d-microservice/latest/text/interacting/a2f-rpc.html
- **Architecture**: https://docs.nvidia.com/ace/audio2face-3d-microservice/latest/text/architecture/audio2face-ms.html
- **Getting Started**: https://docs.nvidia.com/ace/audio2face-3d-microservice/latest/text/getting-started/getting-started.html
- **Sample App**: https://docs.nvidia.com/ace/audio2face-3d-microservice/latest/text/interacting/sample-app.html
- **Animation Data Format**: https://docs.nvidia.com/ace/animation-data-format/latest/index.html
- **Authoring Microservice**: https://docs.nvidia.com/ace/audio2face-3d-authoring-microservice/0.1/text/architecture/audio2face-authoring-ms.html

### Developer Resources
- **ACE page**: https://developer.nvidia.com/ace
- **NIM API Catalog**: https://build.nvidia.com/nvidia/audio2face-3d
- **Audio2Face Discord**: Available via NVIDIA ACE community
- **HuggingFace models**: https://huggingface.co/nvidia/Audio2Face-3D-v3.0
- **PyPI package**: https://pypi.org/project/nvidia-audio2face-3d/
