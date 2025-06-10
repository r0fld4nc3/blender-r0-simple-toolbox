import bpy

from .. import utils as u

_mod = "UTILS.CUSTOM_TRANSFORM"


def get_builtin_transform_orientations(identifiers=False) -> list:
    """
    Get list of built-in transform orientations

    Args:
        identifiers: Return identifiers instead of names
    """
    if identifiers:
        _ret = [i.identifier for i in bpy.types.TransformOrientationSlot.bl_rna.properties["type"].enum_items]
    else:
        _ret = [i.name for i in bpy.types.TransformOrientationSlot.bl_rna.properties["type"].enum_items]

    return _ret


def get_transform_orientations() -> list:
    """
    Returns a list of all transform orientation names

    Uses a workaround to get the names by intentionally
    causing an error with an empty string.
    """
    try:
        # This intentionally raises an exception to get valid values
        u.get_scene().transform_orientation_slots[0].type = ""
    except Exception as inst:
        transforms = str(inst).split("'")[1::2]

    transform_list = list(transforms)
    if u.IS_DEBUG():
        print(f"[DEBUG] [{_mod}] {transform_list=}")

    return transform_list


def get_custom_transform_orientations() -> list:
    """Returns a list of custom transform orientation names"""
    custom_transforms = get_transform_orientations()[7:]  # The 7 first orientations are built-ins
    if u.IS_DEBUG():
        print(f"[DEBUG] [{_mod}] {custom_transforms=}")

    return custom_transforms


def delete_custom_transform_orientation(name: str):
    """Delete a custom transform orientation by name"""
    transform_list = get_custom_transform_orientations()
    for enum_type in transform_list:
        if u.IS_DEBUG():
            print(f"[DEBUG] [{_mod}] {enum_type=} == {name=}")
        if enum_type == name or str(enum_type).lower() == str(name).lower():
            u.get_scene().transform_orientation_slots[0].type = enum_type
            bpy.ops.transform.delete_orientation()
