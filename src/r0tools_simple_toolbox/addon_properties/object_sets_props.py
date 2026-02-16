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

log = logging.getLogger(__name__)


class R0PROP_PG_ObjectSetObjectItem(bpy.types.PropertyGroup):
    """Property representing a reference to an Object within an Object Set"""

    object: bpy.props.PointerProperty(type=bpy.types.Object)  # type: ignore


class R0PROP_PG_ObjectSetEntryItem(bpy.types.PropertyGroup):
    """Property that represents an Object Set that contains a reference to a collection of objects added to the set"""

    _updating = False

    def update_object_set_colour(self, dummy):
        if R0PROP_PG_ObjectSetEntryItem._updating:
            return

        try:
            R0PROP_PG_ObjectSetEntryItem._updating = True
            addon_object_sets_props = u.get_addon_object_sets_props()

            allow_override = addon_object_sets_props.object_sets_colour_allow_override

            for item in self.objects:
                obj = item.object
                if obj is None:
                    continue

                target_colour = self.set_colour
                if not allow_override:
                    containing_sets = u.check_object_in_sets(obj)
                    if containing_sets:
                        target_colour = containing_sets[0].set_colour

                # FIX: Attempt to prevent infinite looping
                if tuple(obj.color) != tuple(target_colour):
                    log.debug(f"Updating color for {obj.name}")
                    obj.color = target_colour
        finally:
            R0PROP_PG_ObjectSetEntryItem._updating = False

    def set_object_set_colour(self, colour: list):
        """
        Set colour of Object Set.
        """

        # update=func passes context as an argument but we want to
        # pass a list of floats. So in order to workaround having
        # to create a new method to support this, let's just
        # enforce that the type(colour) must be in accepted types
        if type(colour) in [type(self.set_colour), list, tuple]:
            self.set_colour = colour

        for item in self.objects:
            obj = item.object
            if obj is None:
                continue

            obj.color = self.set_colour

    name: bpy.props.StringProperty(name="Object Set Name", default="New Object Set")  # type: ignore
    separator: bpy.props.BoolProperty(default=False)  # type: ignore
    default_separator_name = "-" * 16
    uuid: bpy.props.StringProperty(name="Unique ID")  # type: ignore

    objects: bpy.props.CollectionProperty(type=R0PROP_PG_ObjectSetObjectItem)  # type: ignore
    count: bpy.props.IntProperty(name="Count", default=0)  # type: ignore
    set_colour: bpy.props.FloatVectorProperty(  # type: ignore
        name="Set Object Set Colour",
        subtype="COLOR",
        size=4,  # RGBA
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
        update=set_object_set_colour,  # This passes `Context` as an argument....
    )
    checked: bpy.props.BoolProperty(default=False, name="Checked")  # type: ignore
    expanded: bpy.props.BoolProperty(default=False, name="Expand")  # type: ignore
    verts: bpy.props.IntProperty(default=0)  # type: ignore
    edges: bpy.props.IntProperty(default=0)  # type: ignore
    faces: bpy.props.IntProperty(default=0)  # type: ignore
    tris: bpy.props.IntProperty(default=0)  # type: ignore

    def _get_or_build_cache(self):
        """
        Internal method to get the existing object cache (a python set) or
        build it if it doesn't exist or appears outdated.

        Using object pointers keeps references when dealing with object renaming.
        """
        if not hasattr(self, "_object_cache") or len(self._object_cache) != len(self.objects):
            self._object_cache = {item.object.as_pointer() for item in self.objects if item.object}

        return self._object_cache

    def assign_objects(self, objects_to_add: list[bpy.types.Object], force_update: bool = False):
        if self.separator:
            return

        cache = self._get_or_build_cache()

        requires_update = False

        for obj in objects_to_add:
            if not obj:
                continue

            obj_ptr = obj.as_pointer()

            # Add if missing
            if obj_ptr not in cache:
                new_object = self.objects.add()
                new_object.object = obj
                cache.add(obj_ptr)
                requires_update = True

            # Handle Object-level membership
            u.add_set_reference_to_obj(obj, self.uuid)

        if requires_update or force_update:
            self.update_count()

    def remove_objects(self, objects_to_remove: list[bpy.types.Object]):
        addon_object_sets_props = u.get_addon_object_sets_props()

        allow_override = addon_object_sets_props.object_sets_colour_allow_override

        if self.separator:
            return

        if not self.objects:
            return

        pointers_to_remove = {obj.as_pointer() for obj in objects_to_remove if obj}
        cache = self._get_or_build_cache()

        indices_to_remove = []
        successfully_removed_objects = []

        # Identify indices for removal
        for i, item in enumerate(self.objects):
            # Object not longer in scene
            if not item.object:
                indices_to_remove.append(i)
                continue

            # Mark objects targetted for removal
            item_ptr = item.object.as_pointer()
            if item_ptr in pointers_to_remove:
                indices_to_remove.append(i)
                successfully_removed_objects.append(item.object)
                # Update cache
                cache.discard(item_ptr)

        if not indices_to_remove:
            return

        # Remove reversed
        for i, index in enumerate(sorted(indices_to_remove, reverse=True)):
            self.objects.remove(index)

        for obj in successfully_removed_objects:
            # Handle Object-level membership
            u.remove_set_reference_from_obj(obj, self.uuid)

            # Check if object not in other sets
            containing_sets = u.check_object_in_sets(obj)
            if not containing_sets:
                obj.color = (1.0, 1.0, 1.0, 1.0)
            else:
                # Update the object to another set's colour
                if allow_override:
                    obj.color = containing_sets[-1].set_colour
                else:
                    obj.color = containing_sets[0].set_colour

        self.update_count()

    def update_count(self):
        if self.separator:
            return

        self.count = len(self.objects)
        log.debug(f"Updated count for Set '{self.name}': {self.count}")

        self.update_object_set_colour(self)


class R0PROP_UL_ObjectSetsList(bpy.types.UIList):
    """UI List where each entry is an Object Set that itself contains references to Objects added to the set"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        from ..object_sets import SimpleToolbox_OT_SelectObjectSet

        addon_prefs = u.get_addon_prefs()
        addon_object_sets_props = u.get_addon_object_sets_props()

        show_verts = addon_object_sets_props.object_sets_show_mesh_verts
        show_edges = addon_object_sets_props.object_sets_show_mesh_edges
        show_faces = addon_object_sets_props.object_sets_show_mesh_faces
        show_tris = addon_object_sets_props.object_sets_show_mesh_tris

        # Check if the item to insert is a separator
        if item.separator:
            # Draw separator
            row = layout.row()
            row.enabled = False
            row.alignment = "CENTER"
            row.label(text=item.name)
            return

        if self.layout_type in {"DEFAULT", "COMPACT"}:
            main_container = layout.column(align=True)
            row = main_container.row(align=True)

            # Configure accordingly for object sets colour
            if addon_object_sets_props.object_sets_use_colour:
                scale_x = 0.8  # Scales extending the right side to the right
                scale_y = 0.8  # Scales extending the bottom down
                row.separator(factor=0.8)  # Pushes things to the right
                object_set_colour_row = row.row(align=True)
                object_set_colour_row.alignment = "LEFT"
                col = object_set_colour_row.column()
                # col.label(text="", icon="MESH_CUBE")
                col = object_set_colour_row.column()
                col.ui_units_x = scale_x
                col.separator(factor=0.3)  # Pushes things down
                col.scale_y = scale_y
                col.prop(item, "set_colour", text="")
                # Right side padding. Breathing room in case other widget is on the right side
                row.separator(factor=0.5)

            # Info Row
            info_row = row.row(align=True)

            # Select Set
            col_select_set = info_row.row(align=True)
            op = col_select_set.operator(
                SimpleToolbox_OT_SelectObjectSet.bl_idname,
                text="",
                icon="RESTRICT_SELECT_OFF",
            )
            # Set the property before adding to layout
            op.set_index = index
            # Add spacing after the operation is complete
            col_select_set.separator(factor=0.5)

            # Name
            col_name = info_row.row(align=True)
            col_name.prop(item, "name", text="", emboss=False, icon="NONE")

            # Object Count
            col_item_count = info_row.row(align=True)
            col_item_count.alignment = "RIGHT"
            col_item_count.label(text=f"({item.count})", icon="NONE")

            # Fill space to give room to expanded button
            info_row.separator(factor=1.0)

            # Expand/Collapse Mesh Stats
            if any([show_verts, show_edges, show_faces, show_tris]):
                expand_icon = "TRIA_DOWN" if item.expanded else "TRIA_LEFT"
                info_row.prop(item, "expanded", text="", icon=expand_icon, emboss=False)

                if item.expanded:
                    # Indented row
                    stats_row = main_container.row()
                    stats_row.alignment = "LEFT"
                    stats_row.scale_y = 0.9

                    # Indentation
                    split = stats_row.split(factor=0.1)

                    # First part of split is the indentation
                    split.label(text="")

                    # Stats Column
                    col_stats = split.column(align=True)

                    # Vertices
                    if show_verts:
                        row_vert_count = col_stats.row(align=True)
                        row_vert_count.label(text=f" {item.verts:,}", icon="VERTEXSEL")

                    # Edges
                    if show_edges:
                        row_edge_count = col_stats.row(align=True)
                        row_edge_count.label(text=f" {item.edges:,}", icon="EDGESEL")

                    # Faces
                    if show_faces:
                        row_face_count = col_stats.row(align=True)
                        row_face_count.label(text=f" {item.faces:,}", icon="FACESEL")

                    # Triangles
                    if show_tris:
                        row_tri_count = col_stats.row(align=True)
                        row_tri_count.label(text=f" {item.tris:,}", icon="MESH_DATA")

        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text=item.name)


class R0PROP_UL_ObjectSetsViewList(bpy.types.UIList):
    def filter_items(self, context, data, propname):
        """Filter out separator items"""

        items = getattr(data, propname)

        # Filter flags. Default all items to hidden
        flt_flags = [0] * len(items)

        flt_neworder = list(range(len(items)))

        # Filter
        for idx, item in enumerate(items):
            if not item.separator:
                flt_flags[idx] = self.bitflag_filter_item

        return flt_flags, flt_neworder

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        from ..export_ops.operators import SimpleToolbox_OT_ToggleObjectSetSelection

        export_item = u.get_export_set_at_index(u.get_active_export_set_index())

        if not export_item:
            return

        # Check if this Object Set is selected for the current Export Set
        is_selected = any(
            obj_set.name == item.name and obj_set.is_selected for obj_set in export_item.object_sets_names
        )

        row = layout.row()

        # Operator to toggle selection instead of direct property
        icon = "CHECKBOX_HLT" if is_selected else "CHECKBOX_DEHLT"
        op = row.operator(SimpleToolbox_OT_ToggleObjectSetSelection.bl_idname, text="", icon=icon, emboss=False)
        op.export_set_index = u.get_active_export_set_index()
        op.object_set_name = item.name

        # Colour indicator
        col_colour = row.column()
        col_colour.scale_x = 0.3
        col_colour.prop(item, "set_colour", text="")
        col_colour.enabled = False

        row.label(text=item.name)


class r0ObjectSetsProps(bpy.types.PropertyGroup):
    experimental_features: BoolProperty(
        name="Experimental Features",
        description="Enable experimental features",
        default=False,
    )  # type: ignore
    object_sets: CollectionProperty(type=R0PROP_PG_ObjectSetEntryItem)  # type: ignore
    object_sets_index: IntProperty(default=0, name="Object Set")  # type: ignore
    # data_objects: CollectionProperty(type=R0PROP_ObjectSetObjectItem)  # type: ignore
    # scene_objects: CollectionProperty(type=R0PROP_ObjectSetObjectItem)  # type: ignore
    objects_updated: BoolProperty(default=False)  # type: ignore
    object_sets_show_mesh_verts: BoolProperty(default=False, name="Show Total Vertex Count", description="Toggle showing Object Set's total vertex count")  # type: ignore
    object_sets_show_mesh_edges: BoolProperty(default=False, name="Show Total Edge Count", description="Toggle showing Object Set's total edge count")  # type: ignore
    object_sets_show_mesh_faces: BoolProperty(default=False, name="Show Total Face Count", description="Toggle showing Object Set's total face count")  # type: ignore
    object_sets_show_mesh_tris: BoolProperty(default=False, name="Show Total Triangle Count", description="Toggle showing Object Set's total triangle count")  # type: ignore
    object_sets_modal: BoolProperty(
        name="Show Object Sets Modal", description="Show Object Sets Modal Panel", default=False
    )  # type: ignore

    object_sets_use_colour: BoolProperty(
        name="Object Sets Use Colour",
        description="Objects Sets are assigned a colour. Each object within the set is also assigned the colour of the Object Set it is contained in.\nTo view the objects with their assigned colour, change the Viewport Shading either to 'Wire Shading > Object' and/or 'Color > Object'.\nWhen an object is contained in multiple Object Sets, depending on the setting that allows the override, it will display in either the colour of the first Object Set it is found in, or the last",
        default=True,
    )  # type: ignore

    object_sets_colour_allow_override: BoolProperty(
        name="Allow Colour Override",
        description="Allow colour override for objects that area already present in Object Sets and are added or modified in other sets. When disallowed, the object will (hopefully) only retain the colour of the first Object Set is contained in.\nWhen allowed, the object will change colours freely depending on the last modified set, given the object is contained within.",
        default=False,
    )  # type: ignore

    object_sets_modal_width: IntProperty(name="Object Sets Modal Width", default=300, min=0, max=400)  # type: ignore

    object_sets_list_rows: IntProperty(name="Object Sets List Rows", default=8, min=1)  # type: ignore


# ===================================================================
#   Register & Unregister
# ===================================================================
classes = [
    R0PROP_PG_ObjectSetObjectItem,
    R0PROP_PG_ObjectSetEntryItem,
    R0PROP_UL_ObjectSetsList,
    R0PROP_UL_ObjectSetsViewList,
    r0ObjectSetsProps,
]


load_post_handlers = [u.load_legacy_object_sets]


def register():
    for cls in classes:
        log.debug(f"Register {cls.__name__}")
        bpy.utils.register_class(cls)

    log.debug(f"Register bpy.types.Scene.r0fl_object_sets_props")
    bpy.types.Scene.r0fl_object_sets_props = PointerProperty(type=r0ObjectSetsProps, name="r0fl Toolbox Object Sets")

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

    log.debug(f"Unregister bpy.types.Scene.r0fl_object_sets_props")
    del bpy.types.Scene.r0fl_object_sets_props
