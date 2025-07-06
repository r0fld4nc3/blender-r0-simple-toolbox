import bpy
from bpy.props import StringProperty  # type: ignore
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
)

from . import utils as u
from .defines import INTERNAL_NAME
from .keymaps import draw_keymap_settings

_mod = "PROPERTIES"

# ===================================================================
#   ADDON PROPS
# ===================================================================
# Properties which are not stored in preferences


##############################################
###### Custom Object Properties & Items ######
##############################################
class R0PROP_UL_CustomPropertiesList(bpy.types.UIList):
    """UI List where each entry is a custom property belonging to at least 1 selected object"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        if item.type == u.CUSTOM_PROPERTIES_TYPES.OBJECT_DATA:
            row.label(text="", icon="OBJECT_DATA")
        elif item.type == u.CUSTOM_PROPERTIES_TYPES.MESH_DATA:
            row.label(text="", icon="MESH_DATA")
        row.prop(item, "selected", text="")
        row.label(text=item.name)


class R0PROP_PG_CustomPropertyItem(bpy.types.PropertyGroup):
    """Property that represents an entry in the Custom Property UI List"""

    name: StringProperty()  # type: ignore
    selected: BoolProperty(default=False)  # type: ignore
    type: StringProperty(default=u.CUSTOM_PROPERTIES_TYPES.OBJECT_DATA)  # type: ignore


###########################
###### Vertex Groups ######
###########################
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
    if not u.is_writing_context_safe(context.scene):
        return

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
    if u.IS_DEBUG():
        renamed_objects = []
    for obj in context.selected_objects:
        if obj.type in accepted_objects and old_name in obj.vertex_groups:
            obj.vertex_groups[old_name].name = new_name
            renamed_count += 1

            if u.IS_DEBUG():
                renamed_objects.append(obj.name)

    if renamed_count > 0:
        u.LOG(f"[INFO] [{_mod}] Renamed vertex group '{old_name}' to '{new_name}' in {renamed_count} objects")
        if u.IS_DEBUG():
            u.LOG("\t• " + "\n\t• ".join(renamed_objects))


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


########################################
###### Object Sets & Object Items ######
########################################
class R0PROP_ObjectSetObjectItem(bpy.types.PropertyGroup):
    """Property representing a reference to an Object within an Object Set"""

    object: bpy.props.PointerProperty(type=bpy.types.Object)  # type: ignore


class R0PROP_ObjectSetEntryItem(bpy.types.PropertyGroup):
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
            containing_sets = self.check_object_in_sets(obj)
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
    _default_separator_name = "-" * 16

    objects: bpy.props.CollectionProperty(type=R0PROP_ObjectSetObjectItem)  # type: ignore
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

    def assign_object(self, obj):
        if self.separator:
            return

        if not any(o.object == obj for o in self.objects):
            new_object = self.objects.add()
            new_object.object = obj

            self.update_count()

    def remove_object(self, obj):
        addon_prefs = u.get_addon_prefs()
        allow_override = addon_prefs.object_sets_colour_allow_override

        if self.separator:
            return

        for i, o in enumerate(self.objects):
            try:
                if o.object is None:
                    self.objects.remove(i)
                    break

                if o.object and o.object.as_pointer != 0 and o.object == obj or o.object.as_pointer == 0:
                    self.objects.remove(i)
                    break
            except Exception as e:
                print(f"[ERROR] [{_mod}] '{o.object}' {e}")

        # Check if object still exists:
        try:
            valid = u.is_valid_object_global(obj)
        except Exception as e:
            print(f"[ERROR] [{_mod}] Is valid object global check error: {e}")
            self.update_count()
            return

        if valid:
            # Check if object not in other sets
            containing_sets = self.check_object_in_sets(obj)
            if not containing_sets:
                obj.color = (1.0, 1.0, 1.0, 1.0)
            else:
                # Update the object to another set's colour
                if allow_override:
                    obj.color = containing_sets[-1].set_colour
                else:
                    obj.color = containing_sets[0].set_colour

        self.update_count()

    def check_object_in_sets(self, obj) -> list:
        """
        Checks if an object is present in more Object Sets. If so
        return a list of references to each Object Set containing the object

        :return: `list` of `Object Sets`
        """
        addon_props = u.get_addon_props()
        containing_sets = []

        for obj_set in addon_props.object_sets:
            if obj_set.separator:
                continue
            for obj_item in obj_set.objects:
                if obj_item.object == obj:
                    if obj_set not in containing_sets:
                        containing_sets.append(obj_set)

        return containing_sets

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
        from .object_sets import SimpleToolbox_OT_SelectObjectSet

        addon_prefs = u.get_addon_prefs()
        addon_props = u.get_addon_props()

        show_verts = addon_props.object_sets_show_mesh_verts
        show_edges = addon_props.object_sets_show_mesh_edges
        show_faces = addon_props.object_sets_show_mesh_faces
        show_tris = addon_props.object_sets_show_mesh_tris

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


##############################
###### Edge Ops & Items ######
##############################
class R0PROP_BWeightPresetItem(bpy.types.PropertyGroup):
    """Individual bevel weight preset item"""

    value: FloatProperty(
        name="Bevel Weight", description="Bevel weight value", default=0.0, min=0.0, max=1.0
    )  # type: ignore


class R0PROP_PG_EdgeBWeightsPresets(bpy.types.PropertyGroup):
    """Collection of bevel weight presets"""

    presets: CollectionProperty(type=R0PROP_BWeightPresetItem)  # type: ignore
    active_index: IntProperty(default=0, description="Active Index")  # type: ignore


class R0PROP_UL_EdgeBWeightsList(bpy.types.UIList):
    """UI List for bevel weight presets"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        from .data_ops import SimpleToolbox_OT_ApplyBWeightPreset

        # Info Row
        item_row = layout.row(align=True)

        # Apply Preset Button
        col_apply = item_row.row(align=True)
        """
        Store a reference to the Operator and assign it the preset_index property
        so we can apply the specific preset value at this row/index
        without having to first select the row!
        """
        op = col_apply.operator(SimpleToolbox_OT_ApplyBWeightPreset.bl_idname, text="", icon="PLUS")
        # Set the property before adding to layout
        op.preset_index = index
        op.value = item.value
        # Add spacing after the operation is complete
        col_apply.separator(factor=0.5)

        # Preset Value
        item_value = f"{item.value*100:.2f}".split(".")[0] + "%"
        col_value = item_row.row(align=True)
        col_value.label(text=item_value, icon="NONE")

        # Fill space
        item_row.separator(factor=1.0)


# ===================================================================
#   ADDON PROPERTIES
# ===================================================================
class r0SimpleToolboxProps(bpy.types.PropertyGroup):
    # =======================================================================
    # Categories

    cat_show_object_ops: BoolProperty(
        name="Show Object Ops", description="Show operations for Object context", default=True
    )  # type: ignore

    cat_show_mesh_ops: BoolProperty(
        name="Show Mesh Ops", description="Show operations for Mesh context", default=True
    )  # type: ignore

    cat_show_uv_ops: BoolProperty(
        name="Show UV Ops", description="Show operations for UV context", default=False
    )  # type: ignore

    cat_show_find_modifiers_ops: BoolProperty(
        name="Show Find Modifiers", description="Show operations for Finding Modifiers", default=True
    )  # type: ignore

    cat_show_object_sets_editor: BoolProperty(
        name="Show Object Sets Editor", description="Show Object Sets Editor", default=True
    )  # type: ignore

    cat_show_vertex_groups_editor: BoolProperty(
        name="Show Vertex Groups Editor", description="Show Vertex Groups Editor", default=False
    )  # type: ignore

    cat_show_custom_properties_editor: BoolProperty(
        name="Show Custom Properties Editor", description="Show Custom Properties Editor", default=False
    )  # type: ignore

    # =======================================================================

    show_dev_tools: BoolProperty(  # type: ignore
        name="Dev Tools",
        description="Show or hide the development options section",
        default=False,
    )

    show_object_ops: BoolProperty(  # type: ignore
        name="Object Ops",
        description="Show or hide the Object operators section",
        default=True,
    )

    show_mesh_ops: BoolProperty(  # type: ignore
        name="Mesh Ops",
        description="Show or hide the Mesh operators section",
        default=True,
    )

    show_uv_ops: BoolProperty(  # type: ignore
        name="UV Ops",
        description="Show or hide the UV operators section",
        default=False,
    )

    show_experimental_features: BoolProperty(  # type: ignore
        name="Experimental",
        description="Show or hide the Experimental operators section",
        default=False,
    )

    show_uv_island_area_thresholds: BoolProperty(name="UV Island Area Thresholds", default=False)  # type: ignore

    uvisland_sizecheck_arearelative: FloatProperty(  # type: ignore
        name="Relative Area Size",
        description="Area Factor occupied by the UV Island relative to 0 - 1 Space",
        default=0.00001,
        min=0.0,
        max=1.0,
    )

    use_uvisland_sizecheck_arearelative: BoolProperty(  # type: ignore
        name="Use Relative Area Size",
        description="Area Factor occupied by the UV Island relative to 0 - 1 Space",
        default=False,
    )

    uvisland_sizecheck_area_pixelcoverage: FloatProperty(  # type: ignore
        name="Area Pixel Coverage",
        description="Area Squared (px²) of UV Island",
        default=80.0,
        min=0.0,
    )

    use_uvisland_sizecheck_area_pixelcoverage: BoolProperty(  # type: ignore
        name="Use Area Pixel Coverage",
        description="Use Area Squared (px²) of UV Island",
        default=False,
    )

    uvisland_sizecheck_area_pixelpercentage: FloatProperty(  # type: ignore
        name="Area Pixel Percentage",
        description="Percentage Area occupied by the UV Island",
        default=0.001,
        min=0.0,
        max=100.0,
    )

    use_uvisland_sizecheck_area_pixelpercentage: BoolProperty(  # type: ignore
        name="Use Area Pixel Percentage",
        description="Percentage Area occupied by the UV Island",
        default=True,
    )

    show_clear_sharps_on_axis: BoolProperty(  # type: ignore
        name="Clear Sharp Edges on Axis",
        description="Show or hide the Clear Sharps on Axis operator",
        default=False,
    )

    show_ext_ops: BoolProperty(  # type: ignore
        name="External Ops",
        description="Show or hide the External operators section",
        default=False,
    )

    reload_modules_prop: StringProperty(  # type: ignore
        name="Module(s)", description="Command-separated list of module names"
    )

    polygon_threshold: FloatProperty(  # type: ignore
        name="Screen Size Threshold (%)",
        default=1,
        min=0.0,
        max=100.0,
        description="Highlight meshes smaller than this screen size percentage",
    )

    show_custom_property_list_prop: BoolProperty(  # type: ignore
        name="Custom Properties",
        description="List Custom Properties",
        default=False,
    )

    custom_property_list: CollectionProperty(type=R0PROP_PG_CustomPropertyItem)  # type: ignore
    custom_property_list_index: IntProperty(default=0)  # type: ignore
    last_object_selection: StringProperty(  # type: ignore
        name="Last Object Selection",
        description="Comma-separated names of last selected objects",
        default="",
    )

    show_object_sets: BoolProperty(  # type: ignore
        name="Object Sets",
        description="Manage different object selections via an Object Set editor",
        default=False,
    )
    object_sets: CollectionProperty(type=R0PROP_ObjectSetEntryItem)  # type: ignore
    object_sets_index: IntProperty(default=0, name="Object Set")  # type: ignore
    # data_objects: CollectionProperty(type=R0PROP_ObjectSetObjectItem)  # type: ignore
    # scene_objects: CollectionProperty(type=R0PROP_ObjectSetObjectItem)  # type: ignore
    objects_updated: BoolProperty(default=False)  # type: ignore
    object_sets_show_mesh_verts: BoolProperty(default=False, name="Show Total Vertex Count", description="Toggle showing Object Set's total vertex count")  # type: ignore
    object_sets_show_mesh_edges: BoolProperty(default=False, name="Show Total Edge Count", description="Toggle showing Object Set's total edge count")  # type: ignore
    object_sets_show_mesh_faces: BoolProperty(default=False, name="Show Total Face Count", description="Toggle showing Object Set's total face count")  # type: ignore
    object_sets_show_mesh_tris: BoolProperty(default=False, name="Show Total Triangle Count", description="Toggle showing Object Set's total triangle count")  # type: ignore

    show_vertex_groups: BoolProperty(  # type: ignore
        name="Vertex Groups", description="Manage Vertex Groups of selected objects", default=False
    )
    vertex_groups: CollectionProperty(type=R0PROP_PG_VertexGroupPropertyItem)  # type: ignore
    vertex_groups_lock_states: CollectionProperty(type=R0PROP_PG_LockStateEntry)  # type: ignore
    vertex_group_list_index: IntProperty(default=0, name="Vertex Group")  # type: ignore
    vgroups_do_update: BoolProperty(default=True)  # type: ignore

    show_vertex_groups: BoolProperty(  # type: ignore
        name="Vertex Groups", description="Manage Vertex Groups of selected objects", default=False
    )
    vertex_groups: CollectionProperty(type=R0PROP_PG_VertexGroupPropertyItem)  # type: ignore
    vertex_groups_lock_states: CollectionProperty(type=R0PROP_PG_LockStateEntry)  # type: ignore
    vertex_group_list_index: IntProperty(default=0)  # type: ignore
    vgroups_do_update: BoolProperty(default=True)  # type: ignore

    show_find_modifier_search: BoolProperty(  # type: ignore
        name="Find Modifier(s)",
        description="Show Find Object with Modifiers Controls",
        default=False,
    )

    find_modifier_search_text: StringProperty(  # type: ignore
        name="Modifier Type/Name",
        description='Name or Type of Modifier to find.\nTo search for a mix of name and type and/or multiple criteria, use a comma-separated string, ex.: "!!, weld, nodes"\nNote: Case Insensitive',
        default="",
    )

    uv_sizes_options = [
        ("64", "64", "Pixels per kilometer", 0),
        ("128", "128", "Pixels per kilometer", 1),
        ("256", "256", "Pixels per meter", 2),
        ("512", "512", "Pixels per centimeter", 3),
        ("1024", "1024", "Pixels per millimeter", 4),
        ("2048", "2048", "Pixels per micrometer", 5),
        ("4096", "4096", "Pixels per mil", 6),
        ("8192", "8192", "Pixels per mil", 7),
    ]

    uv_size_x: EnumProperty(  # type: ignore
        name="uv_size_x",
        items=uv_sizes_options,
        description="Size of UV Map X",
        default="4096",
        update=lambda self, context: u.save_preferences(),
    )

    uv_size_y: EnumProperty(  # type: ignore
        name="uv_size_x",
        items=uv_sizes_options,
        description="Size of UV Map Y",
        default="4096",
        update=lambda self, context: u.save_preferences(),
    )


class r0SimpleToolboxEdgeDataProps(bpy.types.PropertyGroup):
    vcol_bevel_layer_name: StringProperty(default="BevelToVcol")  # type: ignore
    vcol_crease_layer_name: StringProperty(default="CreaseToVcol")  # type: ignore

    edge_bweights_presets: PointerProperty(type=R0PROP_PG_EdgeBWeightsPresets)  # type: ignore

    apply_as_bevel_weights: BoolProperty(name="As Bevel Weights", description="Apply selected preset value as Edge Bevel Weight", default=True)  # type: ignore
    apply_as_creases: BoolProperty(name="As Creases", description="Apply selected preset value as Crease", default=False)  # type: ignore

    bevel_weights_to_vcol: BoolProperty(name="Bevel Weights", description="Convert Bevel Edge Weights to Vertex Colours", default=True)  # type: ignore

    crease_to_vcol: BoolProperty(name="Creases", description="Convert Creases to Vertex Colours", default=False)  # type: ignore


class r0SimpleToolboxExperimentalProps(bpy.types.PropertyGroup):
    show_edge_data_ops: BoolProperty(
        name="Edge Data Ops", description="Toggle visibility of experimental Edge Data Operators", default=True
    )  # type: ignore


# ===================================================================
#   ADDON PREFS
# ===================================================================
class AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = INTERNAL_NAME

    debug: BoolProperty(name="Debug", description="Set Debug State", default=False)  # type: ignore

    log_output: BoolProperty(name="Log", description="Whehter to produce regular Log output", default=False)  # type: ignore

    lock_states_avoided: IntProperty(
        name="Avoided Locks",
        description="Silly counter to log how many crashes were avoided by forbidden ID context writes",
        default=0,
    )  # type: ignore

    check_update_startup: BoolProperty(
        name="Check Update on Startup",
        description="Flag to set whether to check for extension updates on startup or not",
        default=True,
    )  # type: ignore

    experimental_features: BoolProperty(
        name="Experimental Features",
        description="Enable experimental features",
        default=False,
    )  # type: ignore

    dev_tools: BoolProperty(
        name="Dev Tools",
        description="Enable Dev Tool features",
        default=False,
    )  # type: ignore

    clear_sharp_axis_float_prop: FloatProperty(
        name="Clear Sharp Axis Threshold",
        default=0.0,
        min=0.0,
        description="Threshold value for vertex/edge selection",
        update=lambda self, context: u.save_preferences(),
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

    object_sets_default_colour: FloatVectorProperty(
        name="Object Sets Default Colour",
        subtype="COLOR",
        size=4,  # RGBA
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 1.0),
    )  # type: ignore

    object_sets_modal_width: IntProperty(name="Object Sets Modal Width", default=300, min=0, max=400)  # type: ignore

    object_sets_list_rows: IntProperty(name="Object Sets List Rows", default=6, min=1)  # type: ignore

    custom_properties_list_rows: IntProperty(name="Custom Properties List Rows", default=6, min=1)  # type: ignore

    vertex_groups_list_rows: IntProperty(name="Vertex Groups List Rows", default=8, min=1)  # type: ignore

    #######################
    ### Edge Data Reset ###
    #######################
    edge_reset_sharp: BoolProperty(name="Reset Edge Sharpness", description="Set whether to always reset this component", default=True)  # type: ignore
    edge_reset_seam: BoolProperty(name="Reset Edge Seam", description="Set whether to always reset this component", default=True)  # type: ignore
    edge_reset_crease: BoolProperty(name="Reset Edge Crease", description="Set whether to always reset this component", default=True)  # type: ignore
    edge_reset_bevel_weight: BoolProperty(name="Reset Edge Bevel Weight", description="Set whether to always reset this component", default=True)  # type: ignore

    edge_data_bweight_preset_grid_buttons_toggle: BoolProperty(name="Toggle List/Grid", description="Toggle between a list view or a grid button view", default=False)  # type: ignore

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False

        lock_states_avoided_row = layout.row()
        lock_states_avoided_row.label(text=f"Lock States Avoided: {self.lock_states_avoided}")

        row = layout.row()
        row.prop(self, "debug", text="Debug Mode")

        row = layout.row()
        row.prop(self, "log_output", text="Log Output")

        row = layout.row()
        row.prop(self, "experimental_features", text="Experimental Features")

        row = layout.row()
        row.prop(self, "check_update_startup", text="Check update on startup")

        layout.prop(self, "clear_sharp_axis_float_prop", text="Clear Sharp Edges Threshold")

        # Object Sets
        object_sets_settings_box = layout.box()
        row = object_sets_settings_box.row()
        row.label(text="Object Sets Settings")
        row = object_sets_settings_box.row()
        row.prop(self, "object_sets_modal_width")
        row = object_sets_settings_box.row()
        row.prop(self, "object_sets_list_rows")
        # Object Sets Use Colour
        row = object_sets_settings_box.row()
        row.prop(self, "object_sets_use_colour")

        row = object_sets_settings_box.row()
        row.prop(self, "object_sets_colour_allow_override")

        if self.object_sets_use_colour:
            row = object_sets_settings_box.row()
            row.prop(self, "object_sets_default_colour", text="Default Colour")

        # Custom Properties
        custom_properties_settings_box = layout.box()
        row = custom_properties_settings_box.row()
        row.label(text="Custom Properties Settings")
        row = custom_properties_settings_box.row()
        row.prop(self, "custom_properties_list_rows")

        # Keymaps
        draw_keymap_settings(layout, self)

    def save_axis_threshold(self):
        addon_prefs = bpy.context.preferences.addons[INTERNAL_NAME].preferences
        addon_prefs.clear_sharp_axis_float_prop = self.clear_sharp_axis_float_prop
        # u.LOG(f"[INFO] [{_mod}] Saved Property: clear_sharp_axis_float_prop -> {self.clear_sharp_axis_float_prop}")


# ===================================================================
#   Register & Unregister
# ===================================================================
classes = [
    R0PROP_UL_CustomPropertiesList,
    R0PROP_PG_CustomPropertyItem,
    R0PROP_ObjectSetObjectItem,
    R0PROP_ObjectSetEntryItem,
    R0PROP_UL_ObjectSetsList,
    R0PROP_PG_VertexGroupPropertyItem,
    R0PROP_UL_VertexGroupsList,
    R0PROP_PG_LockStateEntry,
    R0PROP_BWeightPresetItem,
    R0PROP_PG_EdgeBWeightsPresets,
    R0PROP_UL_EdgeBWeightsList,
    AddonPreferences,
    r0SimpleToolboxProps,
    r0SimpleToolboxEdgeDataProps,
    r0SimpleToolboxExperimentalProps,
]


load_post_handlers = [u.initialize_bweight_presets]


def register():
    for cls in classes:
        print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    print(f"[INFO] [{_mod}] Register bpy.types.Scene.r0fl_toolbox_props")
    # Registering to Scene also has the side effect of saving properties on a per scene/file basis, which is nice!
    bpy.types.Scene.r0fl_toolbox_props = PointerProperty(type=r0SimpleToolboxProps)

    print(f"[INFO] [{_mod}] Register bpy.types.Scene.r0fl_toolbox_edge_data_props")
    bpy.types.Scene.r0fl_toolbox_edge_data_props = PointerProperty(type=r0SimpleToolboxEdgeDataProps)

    print(f"[INFO] [{_mod}] Register bpy.types.Scene.r0fl_toolbox_experimental_props")
    bpy.types.Scene.r0fl_toolbox_experimental_props = PointerProperty(type=r0SimpleToolboxExperimentalProps)

    for handler in load_post_handlers:
        print(f"[INFO] [{_mod}] Register load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.append(handler)

    addon_prefs = u.get_addon_prefs()
    global DEBUG
    if addon_prefs.debug:
        DEBUG = True
        print(f"[INFO] [{_mod}] Set Addon Debug to True")
    else:
        DEBUG = False
        print(f"[INFO] [{_mod}] Set Addon Debug to False")


def unregister():
    for cls in classes:
        print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    for handler in load_post_handlers:
        print(f"[INFO] [{_mod}] Unregister load_post_handler: {handler.__name__}")
        bpy.app.handlers.load_post.remove(handler)

    print(f"[INFO] [{_mod}] Unregister bpy.types.Scene.r0fl_toolbox_props")
    del bpy.types.Scene.r0fl_toolbox_props

    print(f"[INFO] [{_mod}] Unregister bpy.types.Scene.r0fl_toolbox_edge_data_props")
    del bpy.types.Scene.r0fl_toolbox_edge_data_props

    print(f"[INFO] [{_mod}] Unregister bpy.types.Scene.r0fl_toolbox_experimental_props")
    del bpy.types.Scene.r0fl_toolbox_experimental_props
