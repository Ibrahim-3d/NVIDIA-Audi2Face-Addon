"""Addon preferences — API key, server URL, default settings."""
import bpy
from bpy.props import StringProperty, EnumProperty, BoolProperty

from . import constants


class A2F_AP_preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    api_key: StringProperty(
        name="API Key",
        description="NVIDIA API key from build.nvidia.com",
        subtype='PASSWORD',
        default="",
    )

    default_model: EnumProperty(
        name="Default Model",
        description="Default Audio2Face-3D model for generation",
        items=[
            ('james_v2.3', "James v2.3", "English male, strong emotion expression"),
            ('claire_v2.3', "Claire v2.3", "Chinese + English female voice"),
            ('mark_v2.3', "Mark v2.3", "English male, high-resolution geometry"),
        ],
        default='james_v2.3',
    )

    connection_mode: EnumProperty(
        name="Default Connection",
        description="Default connection mode for Audio2Face service",
        items=[
            ('CLOUD', "Cloud API", "Use NVIDIA cloud API (grpc.nvcf.nvidia.com)"),
            ('LOCAL', "Local Server", "Connect to a local NIM server"),
        ],
        default='CLOUD',
    )

    server_url: StringProperty(
        name="Local Server URL",
        description="Address of local Audio2Face-3D NIM server (host:port)",
        default=constants.DEFAULT_LOCAL_ENDPOINT,
    )

    auto_create_shapekeys: BoolProperty(
        name="Auto-Create Shape Keys",
        description="Automatically create missing ARKit shape keys on target mesh",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "api_key")
        layout.prop(self, "default_model")
        layout.prop(self, "connection_mode")
        if self.connection_mode == 'LOCAL':
            layout.prop(self, "server_url")
        layout.prop(self, "auto_create_shapekeys")


_classes = (A2F_AP_preferences,)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
