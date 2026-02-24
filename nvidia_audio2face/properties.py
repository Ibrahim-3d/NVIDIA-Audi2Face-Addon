"""Scene properties for Audio2Face addon state."""
import bpy
from bpy.props import (
    StringProperty, PointerProperty, EnumProperty, IntProperty,
    FloatProperty, BoolProperty, CollectionProperty,
)


class A2F_PG_mapping_item(bpy.types.PropertyGroup):
    """Single ARKit-to-Blender shape key mapping entry."""
    arkit_name: StringProperty(name="ARKit Name")
    blender_name: StringProperty(name="Blender Shape Key", default="")
    enabled: BoolProperty(name="Enabled", default=True)
    multiplier: FloatProperty(name="Multiplier", default=1.0, min=0.0, max=5.0)


class A2F_PG_properties(bpy.types.PropertyGroup):
    """Main property group stored on bpy.types.Scene."""

    # -- Core Settings --
    audio_file: StringProperty(
        name="Audio File",
        description="Path to WAV audio file (PCM 16-bit, mono or stereo)",
        subtype='FILE_PATH',
        default="",
    )
    target_mesh: PointerProperty(
        name="Target Mesh",
        description="Mesh object to apply facial animation to",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'MESH',
    )
    model: EnumProperty(
        name="Model",
        description="Audio2Face-3D model to use",
        items=[
            ('james_v2.3', "James v2.3", "English male, strong emotion expression"),
            ('claire_v2.3', "Claire v2.3", "Chinese + English female voice"),
            ('mark_v2.3', "Mark v2.3", "English male, high-resolution geometry"),
        ],
        default='james_v2.3',
    )
    frame_start: IntProperty(
        name="Frame Start",
        description="Frame number where animation begins on the timeline",
        default=1,
        min=0,
    )

    # -- Generation State (transient) --
    is_generating: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})
    generation_progress: FloatProperty(
        default=0.0, min=0.0, max=1.0, subtype='FACTOR',
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    last_status: StringProperty(default="Ready", options={'SKIP_SAVE'})
    last_frame_count: IntProperty(default=0, options={'SKIP_SAVE'})

    # -- Connection --
    connection_mode: EnumProperty(
        name="Connection Mode",
        items=[
            ('CLOUD', "Cloud API", "Use NVIDIA cloud API (grpc.nvcf.nvidia.com)"),
            ('LOCAL', "Local Server", "Connect to a local NIM server"),
        ],
        default='CLOUD',
    )
    server_url: StringProperty(
        name="Server URL",
        description="Address of local Audio2Face-3D NIM server",
        default="localhost:52000",
    )

    # -- Emotion Controls --
    auto_emotion: BoolProperty(
        name="Auto-Detect Emotion",
        description="Let Audio2Emotion detect emotion from audio automatically",
        default=True,
    )
    emotion_strength: FloatProperty(
        name="Emotion Strength", default=0.6, min=0.0, max=2.0, step=10,
    )
    emotion_contrast: FloatProperty(
        name="Emotion Contrast", default=1.0, min=0.0, max=3.0, step=10,
    )
    max_emotions: IntProperty(
        name="Max Emotions", default=3, min=1, max=10,
    )

    # Manual emotion overrides
    emotion_joy: FloatProperty(name="Joy", default=0.0, min=0.0, max=1.0, step=10)
    emotion_anger: FloatProperty(name="Anger", default=0.0, min=0.0, max=1.0, step=10)
    emotion_sadness: FloatProperty(name="Sadness", default=0.0, min=0.0, max=1.0, step=10)
    emotion_fear: FloatProperty(name="Fear", default=0.0, min=0.0, max=1.0, step=10)
    emotion_amazement: FloatProperty(name="Amazement", default=0.0, min=0.0, max=1.0, step=10)
    emotion_disgust: FloatProperty(name="Disgust", default=0.0, min=0.0, max=1.0, step=10)
    emotion_cheekiness: FloatProperty(name="Cheekiness", default=0.0, min=0.0, max=1.0, step=10)
    emotion_grief: FloatProperty(name="Grief", default=0.0, min=0.0, max=1.0, step=10)
    emotion_pain: FloatProperty(name="Pain", default=0.0, min=0.0, max=1.0, step=10)
    emotion_outofbreath: FloatProperty(name="Out of Breath", default=0.0, min=0.0, max=1.0, step=10)

    # -- Face Parameters --
    skin_strength: FloatProperty(name="Skin Strength", default=1.0, min=0.0, max=3.0, step=10)
    upper_face_strength: FloatProperty(name="Upper Face Strength", default=1.0, min=0.0, max=3.0, step=10)
    upper_face_smoothing: FloatProperty(name="Upper Face Smoothing", default=0.001, min=0.0, max=0.1, step=1, precision=4)
    lower_face_strength: FloatProperty(name="Lower Face Strength", default=1.2, min=0.0, max=3.0, step=10)
    lower_face_smoothing: FloatProperty(name="Lower Face Smoothing", default=0.006, min=0.0, max=0.1, step=1, precision=4)
    face_mask_level: FloatProperty(name="Face Mask Level", default=0.6, min=0.0, max=1.0, step=10)
    face_mask_softness: FloatProperty(name="Face Mask Softness", default=0.0085, min=0.0, max=0.1, step=1, precision=4)
    eyelid_open_offset: FloatProperty(name="Eyelid Open Offset", default=0.06, min=-0.5, max=0.5, step=1)
    lip_open_offset: FloatProperty(name="Lip Open Offset", default=-0.02, min=-0.5, max=0.5, step=1)

    # -- Mapping --
    mapping_preset: EnumProperty(
        name="Mapping Preset",
        items=[
            ('ARKIT', "ARKit (Standard)", "Standard ARKit blendshape names"),
            ('VRM', "VRM / VRChat", "VRM blendshape naming convention"),
            ('CUSTOM', "Custom", "Use custom name mapping"),
        ],
        default='ARKIT',
    )
    mapping_items: CollectionProperty(type=A2F_PG_mapping_item)
    mapping_items_index: IntProperty(default=0)


_classes = (A2F_PG_mapping_item, A2F_PG_properties)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.a2f_props = PointerProperty(type=A2F_PG_properties)


def unregister():
    del bpy.types.Scene.a2f_props
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
