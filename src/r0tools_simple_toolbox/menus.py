import logging

import bpy

from .utils import is_debug

log = logging.getLogger(__name__)


class SimpleToolbox_MT_ObjectSetsActionsMenu(bpy.types.Menu):
    bl_idname = "SIMPLETOOLBOX_MT_object_sets_actions"
    bl_label = "Object Sets Actions"

    def draw(self, context):
        from .object_sets import (
            SimpleToolbox_OT_ForceRefreshObjectSets,
            SimpleToolbox_OT_LinkObjectsInObjectSetsToCollections,
            SimpleToolbox_OT_MoveObjectsInObjectSetsToCollections,
            SimpleToolbox_OT_RemoveFromAllObjectSets,
            SimpleToolbox_OT_RenameObjectsInObjectSet,
            SimpleToolbox_OT_UpdateObjectSetsUUIDs,
        )

        layout = self.layout
        layout.operator(SimpleToolbox_OT_ForceRefreshObjectSets.bl_idname, icon="FILE_REFRESH")
        layout.operator(SimpleToolbox_OT_UpdateObjectSetsUUIDs.bl_idname, icon="MOD_BUILD")
        layout.operator(SimpleToolbox_OT_RenameObjectsInObjectSet.bl_idname, icon="OUTLINER_OB_FONT")
        layout.operator(SimpleToolbox_OT_MoveObjectsInObjectSetsToCollections.bl_idname, icon="COLLECTION_NEW")
        layout.operator(SimpleToolbox_OT_LinkObjectsInObjectSetsToCollections.bl_idname, icon="COLLECTION_NEW")
        layout.operator(SimpleToolbox_OT_RemoveFromAllObjectSets.bl_idname, icon="X")


class SimpleToolbox_MT_VertexGroupsActionsMenu(bpy.types.Menu):
    bl_idname = "SIMPLETOOLBOX_MT_vertex_groups_actions"
    bl_label = "Vertex Groups Actions"

    def draw(self, context):
        from .vertex_groups import (
            SimpleToolbox_OT_RemoveUnusedVertexGroups,
            SimpleToolbox_OT_VgroupsLockStateAll,
        )

        layout = self.layout
        # Lock all
        op = layout.operator(SimpleToolbox_OT_VgroupsLockStateAll.bl_idname, text="Lock All", icon="LOCKED")
        op.action = "LOCK"

        # Unlock all
        op = layout.operator(SimpleToolbox_OT_VgroupsLockStateAll.bl_idname, text="Unlock All", icon="UNLOCKED")
        op.action = "UNLOCK"
        layout.operator(SimpleToolbox_OT_RemoveUnusedVertexGroups.bl_idname, icon="X")


def draw_materials_actions_menu(self, context):
    from .operators import SimpleToolbox_OT_RemoveUnusedMaterials

    layout = self.layout
    layout.separator()
    layout.operator(SimpleToolbox_OT_RemoveUnusedMaterials.bl_idname)


# ===================================================================
#   Register & Unregister
# ===================================================================

# fmt: off
classes = [
    SimpleToolbox_MT_ObjectSetsActionsMenu,
    SimpleToolbox_MT_VertexGroupsActionsMenu,
]
# fmt: on


def register():
    for cls in classes:
        if is_debug():
            log.debug(f"Register {cls.__name__}")
        bpy.utils.register_class(cls)

    bpy.types.MATERIAL_MT_context_menu.append(draw_materials_actions_menu)


def unregister():
    for cls in classes:
        if is_debug():
            log.debug(f"Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    bpy.types.MATERIAL_MT_context_menu.remove(draw_materials_actions_menu)

    bpy.types.MATERIAL_MT_context_menu.remove(draw_materials_actions_menu)
