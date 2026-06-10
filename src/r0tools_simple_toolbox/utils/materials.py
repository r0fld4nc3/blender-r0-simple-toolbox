import logging

import bpy

from .. import utils as u

log = logging.getLogger(__name__)


def object_supports_material_slots(obj: bpy.types.Object | None) -> bool:
    return (
        obj is not None and obj.data is not None and hasattr(obj.data, "materials") and hasattr(obj, "material_slots")
    )


def can_duplicate_active_material(context: bpy.types.Context) -> bool:
    obj = u.get_active_object()

    if not object_supports_material_slots(obj):
        log.warning(f"{obj.name} does not support material slots")
        return False

    active_index = obj.active_material_index

    if active_index < 0:
        return False

    if active_index >= len(obj.material_slots):
        return False

    return obj.material_slots[active_index].material is not None


def append_material_to_new_slot(obj: bpy.types.Object, material: bpy.types.Material, *, link: str = "DATA") -> int:
    """
    Append a material to the object's material slots.

    Returns the new slot index.
    """

    obj.data.materials.append(material)

    new_index = len(obj.material_slots) - 1
    new_slot = obj.material_slots[new_index]

    # Preserve whether the source slot was linked to OBJECT or DATA
    try:
        new_slot.link = link
    except TypeError:
        pass

    new_slot.material = material

    return new_index


def move_material_slot_to_index(
    context: bpy.types.Context, obj: bpy.types.Object, *, from_index: int, to_index: int
) -> bool:
    """
    Move the active material slot to a target index using Blender's own slot move operator.

    Keep operator handling native.
    """

    if from_index == to_index:
        return True

    if to_index < 0 or to_index >= len(obj.material_slots):
        return False

    obj.active_material_index = from_index

    direction = "UP" if to_index < from_index else "DOWN"

    with context.temp_override(
        object=obj,
        active_object=obj,
        selected_objects=[obj],
        selected_editable_objects=[obj],
    ):
        while obj.active_material_index != to_index:
            before_index = obj.active_material_index
            result = bpy.ops.object.material_slot_move(direction=direction)

            if "CANCELLED" in result:
                return False

            # Guard for no-op
            if obj.active_material_index == before_index:
                return False

    return True
