import os

import bpy


def to_relative_path(absolute_path: str) -> str:
    """
    Convert an absolute path to Blender-support relative path '//'.
    Falls back to absolute path if path cannot be made relative.
    """

    if not bpy.data.filepath:
        return absolute_path

    try:
        return bpy.path.relpath(absolute_path)
    except ValueError:
        # Can raise ValueError if drives are different on Windows.
        return absolute_path


def to_absolute_path(path: str) -> str:
    """
    Resolve Blender '//' relative path to full absolute path.
    """

    if path.startswith("//"):
        resolved = bpy.path.abspath(path)
    else:
        resolved = path

    return os.path.normpath(os.path.expanduser(resolved))
