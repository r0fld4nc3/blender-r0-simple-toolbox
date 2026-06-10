import logging

import bpy

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
    from .operators import (
        SimpleToolbox_OT_DuplicateActiveMaterial,
        SimpleToolbox_OT_RemoveUnusedMaterials,
    )

    layout = self.layout
    layout.separator()
    layout.operator(SimpleToolbox_OT_RemoveUnusedMaterials.bl_idname)
    layout.operator(SimpleToolbox_OT_DuplicateActiveMaterial.bl_idname)


def draw_materials_operators_cycles_pt(self, context):
    from .operators import (
        SimpleToolbox_OT_DuplicateActiveMaterial,
    )

    layout = self.layout
    ob = context.object
    slot = context.material_slot

    enabled = ob is not None and slot is not None and slot.material is not None

    row = layout.row(align=True)
    row.enabled = enabled

    op = row.operator(SimpleToolbox_OT_DuplicateActiveMaterial.bl_idname, text="Duplicate Material", icon="DUPLICATE")
    op.placement = "AFTER_ACTIVE"
    op.make_active = True


def _safe_remove_callback(cls, callback):
    if cls is None:
        return

    try:
        cls.remove(callback)
    except ValueError:
        pass


def inject_materials_operators(register=True):
    panel_cls = getattr(bpy.types, "CYCLES_PT_context_material", None)

    _safe_remove_callback(panel_cls, draw_materials_operators_cycles_pt)

    if not register:
        return

    if panel_cls is not None:
        panel_cls.append(draw_materials_operators_cycles_pt)


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
        log.debug(f"Register {cls.__name__}")
        bpy.utils.register_class(cls)

    bpy.types.MATERIAL_MT_context_menu.append(draw_materials_actions_menu)

    inject_materials_operators()


def unregister():
    for cls in classes:
        log.debug(f"Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    inject_materials_operators(register=False)

    bpy.types.MATERIAL_MT_context_menu.remove(draw_materials_actions_menu)
