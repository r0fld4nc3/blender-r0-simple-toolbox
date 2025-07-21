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
from ..defines import DEBUG

_mod = "OBJECT SETS PROPS"


class R0PROP_PG_ObjectSetObjectItem(bpy.types.PropertyGroup):
    """Property representing a reference to an Object within an Object Set"""

    object: bpy.props.PointerProperty(type=bpy.types.Object)  # type: ignore


class R0PROP_PG_ObjectSetEntryItem(bpy.types.PropertyGroup):
    """Property that represents an Object Set that contains a reference to a collection of objects added to the set"""

    def update_object_set_colour(self, dummy):
        addon_prefs = u.get_addon_prefs()
        allow_override = addon_prefs.object_sets_colour_allow_override

        for item in self.objects:
            obj = item.object
            if obj is None:
                continue

            obj.color = self.set_colour
            # Check in contained in set
            containing_sets = u.check_object_in_sets(obj)
            if not containing_sets:  # Object not in an Object Set
                if u.IS_DEBUG():
                    print(f"[DEBUG] [{_mod}] Object {obj.name} not present in any Object Set.")
                obj.color = self.set_colour
            elif containing_sets:
                if u.IS_DEBUG():
                    print(
                        f"[DEBUG] [{_mod}] Object {obj.name} contained in {len(containing_sets)} Object Sets. Allow Colour Override is {allow_override}"
                    )
                if not allow_override:
                    obj.color = containing_sets[0].set_colour
                else:
                    # Only allow colour override if flag is set.
                    obj.color = self.set_colour

    def set_object_set_colour(self, colour: list):
        """
        Set colour of Object Set.
        """

        # update=func passes context as an argument but we want to
        # pass a list of floats. So in order to workaround having
        # to create a new method to support this, let's just
        # enfore that the type(colour) must be in accepted types
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

    objects: bpy.props.CollectionProperty(type=R0PROP_PG_ObjectSetObjectItem)  # type: ignore
    _object_cache = set()  # Internal set of object collision management. Helps with checking on a O(1) complexity
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

    def assign_objects(self, objects_to_add: list[bpy.types.Object]):
        if self.separator:
            return

        cache = self._get_or_build_cache()

        for obj in objects_to_add:
            if not obj:
                continue

            obj_ptr = obj.as_pointer()

            if obj_ptr not in cache:
                new_object = self.objects.add()
                new_object.object = obj
                cache.add(obj_ptr)

        self.update_count()

    def remove_objects(self, objects_to_remove: list[bpy.types.Object]):
        addon_prefs = u.get_addon_prefs()
        allow_override = addon_prefs.object_sets_colour_allow_override

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
        if u.IS_DEBUG():
            print(f"[DEBUG] [{_mod}] Updated count for Set '{self.name}': {self.count}")

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
            if addon_prefs.object_sets_use_colour:
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
            """
            OMG this is exciting. So we store a reference to the Operator
            and then we immediately assign it a property defined in the Operator class
            `set_index`. By doing this, we can store which set the button belongs to
            and can select the objects of the given Object Set at a specific row/index
            without having to first select the row!!! Amazing!
            """
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


class r0ObjectSetsProps(bpy.types.PropertyGroup):
    object_sets: CollectionProperty(type=R0PROP_PG_ObjectSetEntryItem)  # type: ignore
    object_sets_index: IntProperty(default=0, name="Object Set")  # type: ignore
    # data_objects: CollectionProperty(type=R0PROP_ObjectSetObjectItem)  # type: ignore
    # scene_objects: CollectionProperty(type=R0PROP_ObjectSetObjectItem)  # type: ignore
    objects_updated: BoolProperty(default=False)  # type: ignore
    object_sets_show_mesh_verts: BoolProperty(default=False, name="Show Total Vertex Count", description="Toggle showing Object Set's total vertex count")  # type: ignore
    object_sets_show_mesh_edges: BoolProperty(default=False, name="Show Total Edge Count", description="Toggle showing Object Set's total edge count")  # type: ignore
    object_sets_show_mesh_faces: BoolProperty(default=False, name="Show Total Face Count", description="Toggle showing Object Set's total face count")  # type: ignore
    object_sets_show_mesh_tris: BoolProperty(default=False, name="Show Total Triangle Count", description="Toggle showing Object Set's total triangle count")  # type: ignore


# ===================================================================
#   Register & Unregister
# ===================================================================
classes = [
    R0PROP_PG_ObjectSetObjectItem,
    R0PROP_PG_ObjectSetEntryItem,
    R0PROP_UL_ObjectSetsList,
    r0ObjectSetsProps,
]


load_post_handlers = [u.load_legacy_object_sets]


def register():
    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    if DEBUG:
        print(f"[INFO] [{_mod}] Register bpy.types.Scene.r0fl_object_sets_props")
    bpy.types.Scene.r0fl_object_sets_props = PointerProperty(type=r0ObjectSetsProps)

    for handler in load_post_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.append(handler)


def unregister():
    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    for handler in load_post_handlers:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.remove(handler)

    if DEBUG:
        print(f"[INFO] [{_mod}] Unregister bpy.types.Scene.r0fl_object_sets_props")
    del bpy.types.Scene.r0fl_object_sets_props
