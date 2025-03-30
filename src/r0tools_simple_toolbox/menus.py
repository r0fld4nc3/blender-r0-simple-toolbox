import bpy


class SimpleToolbox_MT_ObjectSetsActionsMenu(bpy.types.Menu):
    bl_label = "Object Sets Actions"

    def draw(self, context):
        from .operators import SimpleToolbox_OT_RenameObjectsInObjectSet

        layout = self.layout
        layout.operator(SimpleToolbox_OT_RenameObjectsInObjectSet.bl_idname, icon="OUTLINER_OB_FONT")


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
