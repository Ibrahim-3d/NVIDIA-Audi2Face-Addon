bl_info = {
    "name": "Audio2Face for Blender",
    "author": "Ibrahim",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Audio2Face",
    "description": "AI-powered facial animation from audio using NVIDIA Audio2Face-3D",
    "category": "Animation",
}

import importlib
import sys
import os

# Add vendor directory to path for nvidia_ace stubs
_vendor_path = os.path.join(os.path.dirname(__file__), "vendor")
if _vendor_path not in sys.path:
    sys.path.insert(0, _vendor_path)

from . import constants
from . import properties
from . import preferences
from . import operators
from . import panels

_modules = [constants, properties, preferences, operators, panels]


def register():
    for mod in _modules:
        if hasattr(mod, "register"):
            mod.register()


def unregister():
    for mod in reversed(_modules):
        if hasattr(mod, "unregister"):
            mod.unregister()


if __name__ == "__main__":
    register()
