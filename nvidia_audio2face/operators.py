"""Blender operators for Audio2Face addon."""
import asyncio
import csv
import threading
from pathlib import Path

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import constants
from .core import audio, client, mapping, animation, demo_head, transfer


# Thread-safe storage for generation state
_generation_state: client.GenerationState | None = None
_generation_thread: threading.Thread | None = None


def _get_prefs():
    """Get addon preferences."""
    return bpy.context.preferences.addons[__package__].preferences


def _get_props(context):
    """Get scene properties."""
    return context.scene.a2f_props


def _build_face_params(props) -> dict:
    """Build face parameters dict from scene properties."""
    return {
        "upperFaceStrength": props.upper_face_strength,
        "upperFaceSmoothing": props.upper_face_smoothing,
        "lowerFaceStrength": props.lower_face_strength,
        "lowerFaceSmoothing": props.lower_face_smoothing,
        "faceMaskLevel": props.face_mask_level,
        "faceMaskSoftness": props.face_mask_softness,
        "skinStrength": props.skin_strength,
        "eyelidOpenOffset": props.eyelid_open_offset,
        "lipOpenOffset": props.lip_open_offset,
    }


def _build_emotion_params(props) -> dict:
    """Build emotion post-processing parameters from scene properties."""
    return {
        "emotion_contrast": props.emotion_contrast,
        "live_blend_coef": 0.7,
        "enable_preferred_emotion": not props.auto_emotion,
        "preferred_emotion_strength": 0.5,
        "emotion_strength": props.emotion_strength,
        "max_emotions": props.max_emotions,
    }


def _build_manual_emotions(props) -> dict | None:
    """Build manual emotion override dict, or None if auto."""
    if props.auto_emotion:
        return None
    emotions = {
        "amazement": props.emotion_amazement,
        "anger": props.emotion_anger,
        "cheekiness": props.emotion_cheekiness,
        "disgust": props.emotion_disgust,
        "fear": props.emotion_fear,
        "grief": props.emotion_grief,
        "joy": props.emotion_joy,
        "outofbreath": props.emotion_outofbreath,
        "pain": props.emotion_pain,
        "sadness": props.emotion_sadness,
    }
    # Only send if at least one emotion is set
    if any(v > 0.0 for v in emotions.values()):
        return emotions
    return None


def _build_mapping(props) -> dict[str, str]:
    """Build mapping dict from mapping_items or auto-map."""
    if props.mapping_items:
        return {
            item.arkit_name: item.blender_name
            for item in props.mapping_items
            if item.enabled
        }
    # Fallback: auto-map
    if props.target_mesh:
        return mapping.auto_map(props.target_mesh, props.mapping_preset)
    return {}


def _build_multipliers(props) -> dict[str, float] | None:
    """Build per-blendshape multipliers from mapping_items."""
    mults = {}
    for item in props.mapping_items:
        if item.enabled:
            mults[item.arkit_name] = item.multiplier
    return mults if mults else None


def _run_generation(
    mode: str,
    api_key: str,
    function_id: str,
    server_url: str,
    audio_chunks: list[bytes],
    sample_rate: int,
    face_params: dict,
    emotion_params: dict,
    weight_multipliers: dict,
    weight_offsets: dict,
    manual_emotions: dict | None,
    state: client.GenerationState,
):
    """Background thread entry point for generation."""
    async def _async_generate():
        if mode == "CLOUD":
            channel = client.create_cloud_channel(api_key, function_id)
        else:
            channel = client.create_local_channel(server_url)

        try:
            await client.generate_animation(
                channel=channel,
                audio_chunks=audio_chunks,
                sample_rate=sample_rate,
                face_params=face_params,
                emotion_params=emotion_params,
                weight_multipliers=weight_multipliers,
                weight_offsets=weight_offsets,
                manual_emotions=manual_emotions,
                state=state,
            )
        finally:
            await channel.close()

    asyncio.run(_async_generate())


def _poll_generation():
    """Timer callback that polls generation state and applies results."""
    global _generation_state, _generation_thread

    if _generation_state is None:
        return None  # Unregister timer

    scene = bpy.context.scene
    props = scene.a2f_props
    wm = bpy.context.window_manager

    # Safety: check target mesh still exists
    if not props.target_mesh or props.target_mesh.name not in bpy.data.objects:
        props.last_status = "Error: Target mesh was deleted during generation"
        props.is_generating = False
        wm.progress_end()
        _generation_state = None
        _generation_thread = None
        return None

    # Update progress
    props.generation_progress = _generation_state.progress

    if _generation_state.status == "done":
        # Apply animation
        mesh_obj = props.target_mesh
        if mesh_obj and _generation_state.animation_frames:
            mapping_dict = _build_mapping(props)
            multipliers = _build_multipliers(props)

            num_keyframes = animation.apply_animation(
                mesh_obj=mesh_obj,
                frames=_generation_state.animation_frames,
                mapping=mapping_dict,
                scene_fps=scene.render.fps,
                frame_offset=props.frame_start,
                multipliers=multipliers,
            )

            num_frames = len(_generation_state.animation_frames)
            duration = num_frames / constants.A2F_OUTPUT_FPS
            props.last_status = f"Generated {num_frames} frames ({duration:.1f}s)"
            props.last_frame_count = num_frames
        else:
            props.last_status = "Generation completed but no data received"

        props.is_generating = False
        wm.progress_end()
        _generation_state = None
        _generation_thread = None

        # Force UI update
        for area in bpy.context.screen.areas:
            area.tag_redraw()

        return None  # Unregister timer

    elif _generation_state.status == "error":
        props.last_status = f"Error: {_generation_state.error_message}"
        props.is_generating = False
        wm.progress_end()
        _generation_state = None
        _generation_thread = None

        for area in bpy.context.screen.areas:
            area.tag_redraw()

        return None  # Unregister timer

    else:
        # Still running, update progress
        wm.progress_update(int(_generation_state.progress * 100))
        return 0.1  # Continue polling every 100ms


class A2F_OT_generate(bpy.types.Operator):
    """Generate facial animation from audio using Audio2Face-3D"""
    bl_idname = "a2f.generate"
    bl_label = "Generate Facial Animation"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        props = context.scene.a2f_props
        return not props.is_generating

    def execute(self, context):
        global _generation_state, _generation_thread

        props = _get_props(context)
        prefs = _get_prefs()

        # -- Validate inputs --
        if not props.audio_file:
            self.report({'ERROR'}, "No audio file selected. Please choose a WAV file.")
            return {'CANCELLED'}

        if not props.target_mesh:
            self.report({'ERROR'}, "No target mesh selected. Please select a mesh object.")
            return {'CANCELLED'}

        mesh_obj = props.target_mesh
        if not mesh_obj.data.shape_keys:
            if prefs.auto_create_shapekeys:
                # Auto-create shape keys
                mesh_obj.shape_key_add(name="Basis")
                for name in constants.ARKIT_BLENDSHAPE_NAMES:
                    mesh_obj.shape_key_add(name=name)
                self.report({'INFO'}, f"Created {len(constants.ARKIT_BLENDSHAPE_NAMES)} ARKit shape keys.")
            else:
                self.report({'ERROR'}, "Target mesh has no shape keys. Enable auto-create or click 'Create Shape Keys'.")
                return {'CANCELLED'}

        mode = props.connection_mode
        api_key = prefs.api_key
        if mode == "CLOUD" and not api_key:
            self.report({'ERROR'}, "No API key configured. Get one free at build.nvidia.com")
            return {'CANCELLED'}

        # -- Process audio --
        try:
            audio_chunks, sample_rate, info_msgs = audio.process_audio(
                bpy.path.abspath(props.audio_file)
            )
        except audio.AudioError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        for msg in info_msgs:
            self.report({'INFO'}, msg)

        # -- Build config --
        function_id = constants.MODEL_FUNCTION_IDS.get(props.model, "")
        face_params = _build_face_params(props)
        emotion_params = _build_emotion_params(props)
        manual_emotions = _build_manual_emotions(props)

        # Auto-map if needed
        if not props.mapping_items:
            mapping_dict = mapping.auto_map(mesh_obj, props.mapping_preset)
            props.mapping_items.clear()
            for arkit_name in constants.ARKIT_BLENDSHAPE_NAMES:
                item = props.mapping_items.add()
                item.arkit_name = arkit_name
                item.blender_name = mapping_dict.get(arkit_name, "")
                item.enabled = True
                item.multiplier = 1.0

        # -- Start generation --
        _generation_state = client.GenerationState()
        props.is_generating = True
        props.generation_progress = 0.0
        props.last_status = "Generating..."

        context.window_manager.progress_begin(0, 100)

        _generation_thread = threading.Thread(
            target=_run_generation,
            args=(
                mode,
                api_key,
                function_id,
                props.server_url,
                audio_chunks,
                sample_rate,
                face_params,
                emotion_params,
                constants.DEFAULT_WEIGHT_MULTIPLIERS.copy(),
                constants.DEFAULT_WEIGHT_OFFSETS.copy(),
                manual_emotions,
                _generation_state,
            ),
            daemon=True,
        )
        _generation_thread.start()

        bpy.app.timers.register(_poll_generation, first_interval=0.1)

        return {'FINISHED'}


class A2F_OT_test_connection(bpy.types.Operator):
    """Test connection to Audio2Face-3D service"""
    bl_idname = "a2f.test_connection"
    bl_label = "Test Connection"

    @classmethod
    def poll(cls, context):
        return not context.scene.a2f_props.is_generating

    def execute(self, context):
        props = _get_props(context)
        prefs = _get_prefs()

        mode = props.connection_mode
        result = {"done": False, "success": False, "message": ""}

        def _run_check():
            async def _check():
                if mode == "CLOUD":
                    api_key = prefs.api_key
                    function_id = constants.MODEL_FUNCTION_IDS.get(props.model, "")
                    if not api_key:
                        result["done"] = True
                        result["message"] = "No API key configured."
                        return
                    channel = client.create_cloud_channel(api_key, function_id)
                else:
                    channel = client.create_local_channel(props.server_url)

                try:
                    success, message = await client.health_check(channel)
                    result["success"] = success
                    result["message"] = message
                finally:
                    await channel.close()
                    result["done"] = True

            asyncio.run(_check())

        thread = threading.Thread(target=_run_check, daemon=True)
        thread.start()
        thread.join(timeout=10)

        if result["done"]:
            level = 'INFO' if result["success"] else 'ERROR'
            self.report({level}, result["message"])
            props.last_status = result["message"]
        else:
            self.report({'ERROR'}, "Connection test timed out.")
            props.last_status = "Connection timed out"

        return {'FINISHED'}


class A2F_OT_setup_shapekeys(bpy.types.Operator):
    """Create all 52 ARKit shape keys on target mesh"""
    bl_idname = "a2f.setup_shapekeys"
    bl_label = "Create ARKit Shape Keys"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.a2f_props
        return props.target_mesh is not None and props.target_mesh.type == 'MESH'

    def execute(self, context):
        props = _get_props(context)
        mesh_obj = props.target_mesh

        if not mesh_obj.data.shape_keys:
            mesh_obj.shape_key_add(name="Basis")

        existing = {kb.name for kb in mesh_obj.data.shape_keys.key_blocks}
        created = 0

        for name in constants.ARKIT_BLENDSHAPE_NAMES:
            if name not in existing:
                mesh_obj.shape_key_add(name=name)
                created += 1

        already = len(constants.ARKIT_BLENDSHAPE_NAMES) - created
        self.report({'INFO'}, f"Created {created} new shape keys ({already} already existed)")
        return {'FINISHED'}


class A2F_OT_auto_map(bpy.types.Operator):
    """Auto-map shape keys using selected preset"""
    bl_idname = "a2f.auto_map"
    bl_label = "Auto-Map Shape Keys"

    @classmethod
    def poll(cls, context):
        props = context.scene.a2f_props
        return (
            props.target_mesh is not None
            and props.target_mesh.data.shape_keys is not None
        )

    def execute(self, context):
        props = _get_props(context)
        mesh_obj = props.target_mesh

        mapping_dict = mapping.auto_map(mesh_obj, props.mapping_preset)

        # Update mapping_items collection
        props.mapping_items.clear()
        for arkit_name in constants.ARKIT_BLENDSHAPE_NAMES:
            item = props.mapping_items.add()
            item.arkit_name = arkit_name
            item.blender_name = mapping_dict.get(arkit_name, "")
            item.enabled = True
            item.multiplier = 1.0

        mapped, total = mapping.count_mapped(mapping_dict)
        self.report({'INFO'}, f"Mapped {mapped}/{total} shape keys. {total - mapped} unmapped.")
        return {'FINISHED'}


class A2F_OT_clear_animation(bpy.types.Operator):
    """Clear all Audio2Face animation from target mesh"""
    bl_idname = "a2f.clear_animation"
    bl_label = "Clear A2F Animation"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.a2f_props
        return props.target_mesh is not None

    def execute(self, context):
        props = _get_props(context)
        mapping_dict = _build_mapping(props)

        cleared = animation.clear_animation(props.target_mesh, mapping_dict)
        self.report({'INFO'}, f"Cleared animation from {cleared} shape keys.")
        props.last_status = f"Cleared {cleared} shape keys"
        return {'FINISHED'}


class A2F_OT_reset_face_params(bpy.types.Operator):
    """Reset face parameters to defaults"""
    bl_idname = "a2f.reset_face_params"
    bl_label = "Reset to Defaults"

    def execute(self, context):
        props = _get_props(context)
        defaults = constants.DEFAULT_FACE_PARAMS
        props.skin_strength = defaults["skinStrength"]
        props.upper_face_strength = defaults["upperFaceStrength"]
        props.upper_face_smoothing = defaults["upperFaceSmoothing"]
        props.lower_face_strength = defaults["lowerFaceStrength"]
        props.lower_face_smoothing = defaults["lowerFaceSmoothing"]
        props.face_mask_level = defaults["faceMaskLevel"]
        props.face_mask_softness = defaults["faceMaskSoftness"]
        props.eyelid_open_offset = defaults["eyelidOpenOffset"]
        props.lip_open_offset = defaults["lipOpenOffset"]
        self.report({'INFO'}, "Face parameters reset to defaults.")
        return {'FINISHED'}


class A2F_OT_export_csv(bpy.types.Operator, ExportHelper):
    """Export animation data to CSV (NVIDIA format)"""
    bl_idname = "a2f.export_csv"
    bl_label = "Export Animation CSV"

    filename_ext = ".csv"
    filter_glob: StringProperty(default="*.csv", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        props = context.scene.a2f_props
        return props.last_frame_count > 0

    def execute(self, context):
        props = _get_props(context)
        mesh_obj = props.target_mesh

        if not mesh_obj or not mesh_obj.data.shape_keys:
            self.report({'ERROR'}, "No mesh with shape keys to export.")
            return {'CANCELLED'}

        mapping_dict = _build_mapping(props)
        action = mesh_obj.data.shape_keys.animation_data.action if mesh_obj.data.shape_keys.animation_data else None

        if not action:
            self.report({'ERROR'}, "No animation data to export.")
            return {'CANCELLED'}

        # Collect frame range
        frame_start = int(action.frame_range[0])
        frame_end = int(action.frame_range[1])
        scene_fps = context.scene.render.fps

        # Write CSV
        header = ["timeCode"] + [f"blendShapes.{name}" for name in constants.ARKIT_BLENDSHAPE_NAMES]

        with open(self.filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)

            for frame in range(frame_start, frame_end + 1):
                time_code = (frame - frame_start) / scene_fps
                row = [f"{time_code:.6f}"]

                for arkit_name in constants.ARKIT_BLENDSHAPE_NAMES:
                    blender_name = mapping_dict.get(arkit_name, "")
                    value = 0.0
                    if blender_name and blender_name in mesh_obj.data.shape_keys.key_blocks:
                        data_path = f'key_blocks["{blender_name}"].value'
                        fcurve = action.fcurves.find(data_path)
                        if fcurve:
                            value = fcurve.evaluate(frame)
                    row.append(f"{value:.6f}")

                writer.writerow(row)

        num_frames = frame_end - frame_start + 1
        self.report({'INFO'}, f"Exported {num_frames} frames to {self.filepath}")
        return {'FINISHED'}


class A2F_OT_import_csv(bpy.types.Operator, ImportHelper):
    """Import animation data from CSV (NVIDIA format)"""
    bl_idname = "a2f.import_csv"
    bl_label = "Import Animation CSV"

    filename_ext = ".csv"
    filter_glob: StringProperty(default="*.csv", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        props = context.scene.a2f_props
        return props.target_mesh is not None

    def execute(self, context):
        props = _get_props(context)
        mesh_obj = props.target_mesh

        if not mesh_obj:
            self.report({'ERROR'}, "No target mesh selected.")
            return {'CANCELLED'}

        if not mesh_obj.data.shape_keys:
            self.report({'ERROR'}, "Target mesh has no shape keys.")
            return {'CANCELLED'}

        # Parse CSV
        frames = []
        try:
            with open(self.filepath, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    time_code = float(row.get("timeCode", 0.0))
                    weights = {}
                    for col_name, value in row.items():
                        if col_name.startswith("blendShapes."):
                            arkit_name = col_name.replace("blendShapes.", "")
                            weights[arkit_name] = float(value)
                    if weights:
                        frames.append(client.AnimationFrame(
                            time_code=time_code,
                            weights=weights,
                        ))
        except Exception as e:
            self.report({'ERROR'}, f"Failed to parse CSV: {e}")
            return {'CANCELLED'}

        if not frames:
            self.report({'ERROR'}, "No animation data found in CSV.")
            return {'CANCELLED'}

        # Apply
        mapping_dict = _build_mapping(props)
        num_keyframes = animation.apply_animation(
            mesh_obj=mesh_obj,
            frames=frames,
            mapping=mapping_dict,
            scene_fps=context.scene.render.fps,
            frame_offset=props.frame_start,
        )

        self.report({'INFO'}, f"Imported {len(frames)} frames ({num_keyframes} keyframes).")
        props.last_status = f"Imported {len(frames)} frames"
        props.last_frame_count = len(frames)
        return {'FINISHED'}


class A2F_OT_load_demo_head(bpy.types.Operator):
    """Create a demo head with 52 ARKit blendshape deformations for testing"""
    bl_idname = "a2f.load_demo_head"
    bl_label = "Load Demo Head"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = demo_head.create_demo_head()
        props = _get_props(context)
        props.target_mesh = obj
        props.template_mesh = obj

        self.report({'INFO'}, f"Created demo head '{obj.name}' with 52 ARKit blendshapes")
        return {'FINISHED'}


class A2F_OT_transfer_shapekeys(bpy.types.Operator):
    """Transfer ARKit blendshape deformations from template mesh to target mesh"""
    bl_idname = "a2f.transfer_shapekeys"
    bl_label = "Transfer Shape Keys"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.a2f_props
        return (
            props.template_mesh is not None
            and props.target_mesh is not None
            and props.template_mesh != props.target_mesh
            and props.template_mesh.data.shape_keys is not None
        )

    def execute(self, context):
        props = _get_props(context)

        try:
            count = transfer.transfer_shape_keys(
                source_obj=props.template_mesh,
                target_obj=props.target_mesh,
            )
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        self.report({'INFO'}, f"Transferred {count} shape keys to '{props.target_mesh.name}'")
        return {'FINISHED'}


_classes = (
    A2F_OT_generate,
    A2F_OT_test_connection,
    A2F_OT_setup_shapekeys,
    A2F_OT_auto_map,
    A2F_OT_clear_animation,
    A2F_OT_reset_face_params,
    A2F_OT_export_csv,
    A2F_OT_import_csv,
    A2F_OT_load_demo_head,
    A2F_OT_transfer_shapekeys,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    global _generation_state, _generation_thread
    _generation_state = None
    _generation_thread = None
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
