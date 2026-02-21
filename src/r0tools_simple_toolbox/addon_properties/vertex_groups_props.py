import logging

import bpy
from bpy.props import (  # type: ignore
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

from .. import utils as u
from ..vertex_groups.vertex_groups import _vertex_group_sync_selection

log = logging.getLogger(__name__)


class R0PROP_UL_VertexGroupsList(bpy.types.UIList):
    """UI List where each entry is a vertex group belonging to at least 1 selected object"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.alignment = "LEFT"
        row.label(text="", icon="GROUP_VERTEX")
        row.prop(item, "selected", text="")
        row.prop(item, "locked", text="", icon_only=True, icon="LOCKED" if item.locked else "UNLOCKED", emboss=False)
        row.label(text=f"({item.count})")
        # Conditionally allow renaming based on lock status
        if item.locked:
            row.label(text=item.name)
        else:
            # Need a scaled row to keep layout and also display full name without being cut-off
            scaled_row = row.row()
            scaled_row.scale_x = 2.0
            scaled_row.prop(item, "name", text="", emboss=False)


def update_lock_state_callback(self, context):
    vertex_group_name = self.name

    # Update persistent state
    found = False
    for state in u.iter_vertex_groups_lock_states():
        if state.name == vertex_group_name:
            state.locked = self.locked
            found = True
            break

    if not found:
        states = u.get_vertex_groups_lock_states()
        if states is not None:
            new_state = states.add()
            new_state.name = vertex_group_name
            new_state.locked = self.locked


def update_vertex_group_name_callback(self, context):
    if not hasattr(self, "previous_name"):
        return

    old_name = getattr(self, "previous_name", self.name)
    new_name = self.name

    accepted_objects = [u.OBJECT_TYPES.MESH]

    # Store current name for future reference
    self.previous_name = new_name

    # Skip if name hasn't changed
    if old_name == new_name:
        return

    # Do renaming
    renamed_count = 0
    renamed_objects = []
    for obj in context.selected_objects:
        if obj.type in accepted_objects and old_name in obj.vertex_groups:
            obj.vertex_groups[old_name].name = new_name
            renamed_count += 1

            renamed_objects.append(obj.name)

    if renamed_count > 0:
        from ..vertex_groups import vertex_groups_list_update

        log.info(f"Renamed vertex group '{old_name}' to '{new_name}' in {renamed_count} objects")
        log.debug("\t• " + "\n\t• ".join(renamed_objects))

        # Update list to prevent mismatched assignments
        vertex_groups_list_update(force=True)

        # Sync the active index to the renamed entry
        addon_vertex_groups_props = u.get_addon_vertex_groups_props()
        if addon_vertex_groups_props:
            # Find new index of renamed item in the collection
            new_index = next(
                (i for i, vg in enumerate(addon_vertex_groups_props.vertex_groups) if vg.name == new_name),
                -1,
            )
            if new_index != -1:
                # Setting this triggers update_vertex_group_list_index_callback,
                # which calls _vertex_group_sync_selection automatically.
                addon_vertex_groups_props.vertex_group_list_index = new_index


def update_vertex_group_list_index_callback(self, context):
    """Callback function for when the active index/entry is updated in the UIList"""

    # Sync Vertex Group selection across selected Objects
    _vertex_group_sync_selection(self, context)


class R0PROP_PG_VertexGroupPropertyItem(bpy.types.PropertyGroup):
    """Property that represent an entry in the Vertex Groups UI List"""

    name: StringProperty(name="Vertex Group Name", update=update_vertex_group_name_callback)  # type: ignore
    count: IntProperty(default=0, name="Object Count", description="Count of objects where this vertex group belongs to")  # type: ignore
    locked: BoolProperty(default=False, name="Locked", update=update_lock_state_callback, description="Locks the vertex group to prevent modification, such as deletion")  # type: ignore
    selected: BoolProperty(default=False, name="Selected")  # type: ignore

    # Store previous name for rename ops
    previous_name: StringProperty(name="Previous Name")  # type: ignore


class R0PROP_PG_LockStateEntry(bpy.types.PropertyGroup):
    name: StringProperty()  # type: ignore
    locked: IntProperty(default=False)  # type: ignore


class r0VertexGroupsProps(bpy.types.PropertyGroup):
    vertex_groups: CollectionProperty(type=R0PROP_PG_VertexGroupPropertyItem)  # type: ignore
    vertex_groups_lock_states: CollectionProperty(type=R0PROP_PG_LockStateEntry)  # type: ignore
    vertex_group_list_index: IntProperty(default=0, name="Vertex Group", update=update_vertex_group_list_index_callback)  # type: ignore
    vgroups_do_update: BoolProperty(default=True)  # type: ignore
    vertex_groups_list_rows: IntProperty(name="Vertex Groups List Rows", default=8, min=1)  # type: ignore
    sync_selection: BoolProperty(default=True, name="Sync Selection", description="Sync active vertex group selection from UIList to selected objects")  # type: ignore


# ===================================================================
#   Register & Unregister
# ===================================================================
classes = [
    R0PROP_PG_VertexGroupPropertyItem,
    R0PROP_UL_VertexGroupsList,
    R0PROP_PG_LockStateEntry,
    r0VertexGroupsProps,
]


load_post_handlers = []


def register():
    for cls in classes:
        log.debug(f"Register {cls.__name__}")
        bpy.utils.register_class(cls)

    log.debug(f"Register bpy.types.Scene.r0fl_vertex_groups_props")
    bpy.types.Scene.r0fl_vertex_groups_props = PointerProperty(
        type=r0VertexGroupsProps, name="r0fl Toolbox Vertex Groups"
    )

    for handler in load_post_handlers:
        log.debug(f"Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.append(handler)


def unregister():
    for cls in classes:
        log.debug(f"Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    for handler in load_post_handlers:
        log.debug(f"Unregister load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.remove(handler)

    log.debug(f"Unregister bpy.types.Scene.r0fl_vertex_groups_props")
    del bpy.types.Scene.r0fl_vertex_groups_props
