import bpy

_mod = "MENUS"


class SimpleToolbox_MT_ObjectSetsActionsMenu(bpy.types.Menu):
    bl_idname = "SIMPLETOOLBOX_MT_object_sets_actions"
    bl_label = "Object Sets Actions"

    def draw(self, context):
        from .object_sets import (
            SimpleToolbox_OT_ForceRefreshObjectSets,
            SimpleToolbox_OT_LinkObjectsInObjectSetsToCollections,
            SimpleToolbox_OT_MoveObjectsInObjectSetsToCollections,
            SimpleToolbox_OT_RenameObjectsInObjectSet,
        )

        layout = self.layout
        layout.operator(SimpleToolbox_OT_ForceRefreshObjectSets.bl_idname, icon="FILE_REFRESH")
        layout.operator(SimpleToolbox_OT_RenameObjectsInObjectSet.bl_idname, icon="OUTLINER_OB_FONT")
        layout.operator(SimpleToolbox_OT_MoveObjectsInObjectSetsToCollections.bl_idname, icon="COLLECTION_NEW")
        layout.operator(SimpleToolbox_OT_LinkObjectsInObjectSetsToCollections.bl_idname, icon="COLLECTION_NEW")


class SimpleToolbox_MT_VertexGroupsActionsMenu(bpy.types.Menu):
    bl_idname = "SIMPLETOOLBOX_MT_vertex_groups_actions"
    bl_label = "Vertex Groups Actions"

    def draw(self, context):
        from .vertex_groups import SimpleToolbox_OT_RemoveUnusedVertexGroups

        layout = self.layout
        layout.operator(SimpleToolbox_OT_RemoveUnusedVertexGroups.bl_idname, icon="X")


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
        print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
