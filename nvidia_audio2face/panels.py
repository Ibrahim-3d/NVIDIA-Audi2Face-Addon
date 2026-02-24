"""UI panels for Audio2Face addon in 3D Viewport sidebar."""
import bpy

from . import constants
from .core.mapping import count_mapped


class A2F_PT_main(bpy.types.Panel):
    """Main Audio2Face panel"""
    bl_label = "Audio2Face"
    bl_idname = "A2F_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Audio2Face"

    def draw(self, context):
        layout = self.layout
        props = context.scene.a2f_props

        # Audio file
        layout.prop(props, "audio_file")

        # Target mesh
        layout.prop(props, "target_mesh")

        # Model
        layout.prop(props, "model")

        # Frame start
        layout.prop(props, "frame_start")

        layout.separator()

        # Generate button
        row = layout.row(align=True)
        row.scale_y = 1.5
        if props.is_generating:
            row.enabled = False
            pct = int(props.generation_progress * 100)
            row.operator("a2f.generate", text=f"Generating... {pct}%", icon='SORTTIME')
        else:
            row.operator("a2f.generate", text="Generate Animation", icon='PLAY')

        # Status
        if props.last_status:
            box = layout.box()
            if "Error" in props.last_status:
                box.alert = True
            box.label(text=props.last_status, icon='INFO')

        layout.separator()

        # Action buttons row
        row = layout.row(align=True)
        row.operator("a2f.clear_animation", text="Clear", icon='TRASH')
        row.operator("a2f.export_csv", text="Export CSV", icon='EXPORT')
        row.operator("a2f.import_csv", text="Import CSV", icon='IMPORT')


class A2F_PT_model_setup(bpy.types.Panel):
    """Quick Start: demo model and shape key transfer"""
    bl_label = "Model Setup"
    bl_idname = "A2F_PT_model_setup"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Audio2Face"
    bl_parent_id = "A2F_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.a2f_props

        # Demo head section
        box = layout.box()
        box.label(text="Quick Start", icon='LIGHT')
        col = box.column(align=True)
        col.label(text="No face model? Create a demo head with")
        col.label(text="52 ARKit blendshapes to get started:")
        col.separator()
        col.operator("a2f.load_demo_head", icon='MONKEY')

        layout.separator()

        # Transfer section
        box = layout.box()
        box.label(text="Transfer Blendshapes", icon='MOD_DATA_TRANSFER')
        col = box.column(align=True)
        col.label(text="Copy shape key deformations from a")
        col.label(text="template to your custom mesh:")
        col.separator()
        col.prop(props, "template_mesh", icon='MESH_DATA')
        col.prop(props, "target_mesh", text="Target", icon='OUTLINER_OB_MESH')
        col.separator()
        row = col.row()
        row.scale_y = 1.3
        row.operator("a2f.transfer_shapekeys", icon='PASTEDOWN')

        # Status hint
        if props.template_mesh and props.target_mesh:
            if props.template_mesh == props.target_mesh:
                col.label(text="Template and target must be different", icon='ERROR')
            elif not props.template_mesh.data.shape_keys:
                col.label(text="Template has no shape keys", icon='ERROR')


class A2F_PT_emotion(bpy.types.Panel):
    """Emotion controls sub-panel"""
    bl_label = "Emotion Controls"
    bl_idname = "A2F_PT_emotion"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Audio2Face"
    bl_parent_id = "A2F_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.a2f_props

        layout.prop(props, "auto_emotion")

        layout.separator()

        layout.prop(props, "emotion_strength")
        layout.prop(props, "emotion_contrast")
        layout.prop(props, "max_emotions")

        if not props.auto_emotion:
            layout.separator()
            layout.label(text="Manual Emotion Override:")

            col = layout.column(align=True)
            col.prop(props, "emotion_joy")
            col.prop(props, "emotion_anger")
            col.prop(props, "emotion_sadness")
            col.prop(props, "emotion_fear")
            col.prop(props, "emotion_amazement")
            col.prop(props, "emotion_disgust")
            col.prop(props, "emotion_cheekiness")
            col.prop(props, "emotion_grief")
            col.prop(props, "emotion_pain")
            col.prop(props, "emotion_outofbreath")


class A2F_PT_face_params(bpy.types.Panel):
    """Face parameters sub-panel"""
    bl_label = "Face Parameters"
    bl_idname = "A2F_PT_face_params"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Audio2Face"
    bl_parent_id = "A2F_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.a2f_props

        col = layout.column(align=True)
        col.prop(props, "skin_strength")
        col.prop(props, "upper_face_strength")
        col.prop(props, "upper_face_smoothing")
        col.prop(props, "lower_face_strength")
        col.prop(props, "lower_face_smoothing")
        col.prop(props, "face_mask_level")
        col.prop(props, "face_mask_softness")
        col.prop(props, "eyelid_open_offset")
        col.prop(props, "lip_open_offset")

        layout.separator()
        layout.operator("a2f.reset_face_params", icon='LOOP_BACK')


class A2F_PT_mapping(bpy.types.Panel):
    """Shape key mapping sub-panel"""
    bl_label = "Shape Key Mapping"
    bl_idname = "A2F_PT_mapping"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Audio2Face"
    bl_parent_id = "A2F_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.a2f_props

        layout.prop(props, "mapping_preset")

        row = layout.row(align=True)
        row.operator("a2f.auto_map", text="Auto-Map", icon='FILE_REFRESH')
        row.operator("a2f.setup_shapekeys", text="Create Missing", icon='ADD')

        # Show mapping status
        if props.mapping_items:
            mapping_dict = {
                item.arkit_name: item.blender_name
                for item in props.mapping_items
            }
            mapped, total = count_mapped(mapping_dict)
            layout.label(text=f"Status: {mapped}/{total} mapped")

            # Show mapping list (scrollable)
            box = layout.box()
            col = box.column(align=True)
            for item in props.mapping_items:
                row = col.row(align=True)
                row.prop(item, "enabled", text="")

                sub = row.split(factor=0.45, align=True)
                sub.label(text=item.arkit_name)

                if item.blender_name:
                    sub.label(text=item.blender_name)
                else:
                    sub.alert = True
                    sub.label(text="(unmapped)")

                row.prop(item, "multiplier", text="", slider=True)


class A2F_PT_settings(bpy.types.Panel):
    """Connection settings sub-panel"""
    bl_label = "Connection Settings"
    bl_idname = "A2F_PT_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Audio2Face"
    bl_parent_id = "A2F_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.a2f_props
        prefs = context.preferences.addons[__package__].preferences

        layout.prop(props, "connection_mode", expand=True)

        layout.separator()

        if props.connection_mode == 'CLOUD':
            layout.prop(prefs, "api_key")
            layout.label(text="Get a free key at build.nvidia.com", icon='URL')
        else:
            layout.prop(props, "server_url")

        layout.separator()
        layout.operator("a2f.test_connection", icon='LINKED')


_classes = (
    A2F_PT_main,
    A2F_PT_model_setup,
    A2F_PT_emotion,
    A2F_PT_face_params,
    A2F_PT_mapping,
    A2F_PT_settings,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
