# Audio2Face for Blender

AI-powered facial animation from audio using NVIDIA Audio2Face-3D. Converts speech audio into 52 ARKit blendshape animations directly inside Blender.

<!-- screenshot placeholder -->

## Features

- **One-click generation** — Select audio file, pick a mesh, hit Generate
- **52 ARKit blendshapes** — Full Apple ARKit standard blendshape set
- **3 voice models** — James (English male), Claire (Chinese + English female), Mark (English male, high-res)
- **Emotion controls** — Auto-detect from audio or manually set 10 emotions (joy, anger, sadness, fear, amazement, disgust, cheekiness, grief, pain, out-of-breath)
- **Face parameter tuning** — Upper/lower face strength, smoothing, skin strength, eyelid/lip offsets
- **Shape key mapping** — ARKit and VRM/VRChat presets with per-blendshape multipliers
- **Auto-create shape keys** — Automatically adds missing ARKit shape keys to any mesh
- **CSV import/export** — NVIDIA-format CSV for interop with other tools
- **Cloud + Local** — Use NVIDIA's free cloud API or a self-hosted NIM server
- **Background processing** — Non-blocking generation with progress bar

## Quick Start

### 1. Install the Addon

**Option A: From ZIP**
1. Download or build the `nvidia_audio2face/` directory as a ZIP
2. In Blender: Edit > Preferences > Add-ons > Install from Disk
3. Select the ZIP file and enable "Audio2Face for Blender"

**Option B: Manual**
1. Copy the `nvidia_audio2face/` folder into your Blender addons directory:
   - Windows: `%APPDATA%\Blender Foundation\Blender\4.2\extensions\`
   - macOS: `~/Library/Application Support/Blender/4.2/extensions/`
   - Linux: `~/.config/blender/4.2/extensions/`
2. Enable the addon in Blender preferences

### 2. Get an NVIDIA API Key (Free)

1. Go to [build.nvidia.com](https://build.nvidia.com)
2. Create a free account
3. Navigate to Audio2Face-3D and generate an API key
4. Paste the key in the addon's Connection Settings panel (or Edit > Preferences > Add-ons > Audio2Face)

### 3. Select Audio

- In the 3D Viewport sidebar, open the **Audio2Face** tab
- Click the file browser next to **Audio File** and select a WAV file
- Supported: 16-bit PCM WAV, mono or stereo, any sample rate (auto-converted to 16kHz)
- Maximum duration: 5 minutes

### 4. Select Target Mesh

- Set **Target Mesh** to any mesh object in your scene
- If the mesh doesn't have ARKit shape keys, click **Create Missing** in the Shape Key Mapping panel (or enable auto-create in addon preferences)

### 5. Generate

- Click **Generate Animation**
- Watch the progress bar update in real-time
- When complete, keyframes are automatically applied to the timeline
- Scrub through the timeline to see the facial animation

## Audio Requirements

| Property | Requirement |
|----------|-------------|
| Format | WAV (PCM) |
| Bit depth | 16-bit |
| Channels | Mono or Stereo (auto-converted to mono) |
| Sample rate | Any (auto-resampled to 16kHz if needed; 32kHz/48kHz passed through) |
| Duration | 0.1 seconds to 5 minutes |

## Connection Modes

### Cloud API (Default)
- Uses `grpc.nvcf.nvidia.com:443` with SSL
- Requires a free NVIDIA API key from [build.nvidia.com](https://build.nvidia.com)
- No local GPU required

### Local Server
- Connect to a self-hosted Audio2Face-3D NIM container
- Set the server address (default: `localhost:52000`)
- No API key needed
- Requires NVIDIA GPU with NIM installed

## Shape Key Mapping

The addon supports three mapping presets:

- **ARKit (Standard)** — Matches standard ARKit blendshape names (case-insensitive)
- **VRM / VRChat** — Maps VRM naming convention (e.g., `Fcl_MTH_Smile_L` to `MouthSmileLeft`)
- **Custom** — Falls back to ARKit name matching; edit individual mappings in the list

Each mapping entry has:
- **Enable/Disable** toggle
- **ARKit Name** (source from NVIDIA)
- **Blender Shape Key** (target on your mesh)
- **Multiplier** slider (0.0 to 5.0)

## CSV Import/Export

Export animation to NVIDIA-compatible CSV format:
```
timeCode,blendShapes.EyeBlinkLeft,blendShapes.EyeLookDownLeft,...
0.000000,0.012345,0.000000,...
0.033333,0.015678,0.000000,...
```

This format is compatible with other NVIDIA Audio2Face tools and can be imported back into Blender or used in game engines.

## Troubleshooting

**"Invalid API key"**
- Verify your key at [build.nvidia.com](https://build.nvidia.com)
- Make sure you copied the full key including the `nvapi-` prefix

**"Cannot connect to Audio2Face service"**
- Check your internet connection (Cloud mode)
- Verify the server address and that the NIM container is running (Local mode)
- Try the **Test Connection** button in Connection Settings

**"Audio must be 16-bit PCM WAV"**
- Convert your audio to 16-bit WAV using Audacity or ffmpeg:
  ```
  ffmpeg -i input.mp3 -acodec pcm_s16le -ar 16000 -ac 1 output.wav
  ```

**No animation appears after generation**
- Check that your mesh has shape keys (use **Create Missing**)
- Check the mapping panel — unmapped entries show "(unmapped)" in red
- Click **Auto-Map** after creating shape keys

**Shape keys exist but aren't mapped**
- Your shape key names may not match ARKit names
- Try the **VRM** preset if using VRM/VRChat models
- Manually edit mappings in the Shape Key Mapping panel

## Requirements

- Blender 4.2 or later
- Python 3.11 (bundled with Blender 4.2+)
- Internet connection (Cloud mode) or local NIM server (Local mode)

## License

This addon is licensed under GPL-3.0-or-later (required for Blender extensions).

Bundled dependencies:
- `nvidia_ace` protobuf stubs — MIT License (NVIDIA)
- `grpcio` — Apache License 2.0
- `protobuf` — BSD 3-Clause License

See `LICENSES/` directory for full license texts.
