import bpy


class SimpleToolbox_MT_ObjectSetsActionsMenu(bpy.types.Menu):
    bl_idname = "r0tools.object_sets_actions_menu"
    bl_label = "Object Sets Actions"

    def draw(self, context):
        from .operators import (
            SimpleToolbox_OT_ForceRefreshObjectSets,
            SimpleToolbox_OT_MoveObjectsInObjectSetsToCollections,
            SimpleToolbox_OT_RenameObjectsInObjectSet,
        )

        layout = self.layout
        layout.operator(SimpleToolbox_OT_ForceRefreshObjectSets.bl_idname, icon="FILE_REFRESH")
        layout.operator(SimpleToolbox_OT_RenameObjectsInObjectSet.bl_idname, icon="OUTLINER_OB_FONT")
        layout.operator(SimpleToolbox_OT_MoveObjectsInObjectSetsToCollections.bl_idname, icon="COLLECTION_NEW")


# ===================================================================
#   Register & Unregister
# ===================================================================

# fmt: off
classes = [
    SimpleToolbox_MT_ObjectSetsActionsMenu,
]
# fmt: on


def register():
    for cls in classes:
        print(f"[MENUS] Register {cls.__name__}")
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        print(f"[MENUS] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
