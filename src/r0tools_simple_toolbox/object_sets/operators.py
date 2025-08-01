import random

import bpy
from bpy.props import BoolProperty, FloatVectorProperty, IntProperty, StringProperty

from .. import utils as u
from ..defines import DEBUG
from .object_sets import *

_mod = "OBJECT_SETS.OPERATORS"


class SimpleToolbox_OT_ObjectSetsModal(bpy.types.Operator):
    """Floating Modal Panel that can be drawn wherever in the UI"""

    bl_idname = "r0tools.object_sets_modal"
    bl_label = "Object Sets Modal"

    def invoke(self, context, event):
        addon_object_sets_props = u.get_addon_object_sets_props()
        addon_object_sets_props.object_sets_modal = True
        object_sets_modal_prefs_width = u.get_addon_object_sets_props().object_sets_modal_width
        return context.window_manager.invoke_props_dialog(self, width=object_sets_modal_prefs_width)

    def execute(self, context):
        addon_object_sets_props = u.get_addon_object_sets_props()
        addon_object_sets_props.object_sets_modal = False
        return {"FINISHED"}

    def cancel(self, context):
        addon_object_sets_props = u.get_addon_object_sets_props()
        addon_object_sets_props.object_sets_modal = False

    def modal(self, context, event):

        if event.type == "MOUSEMOVE":  # Ignore mouse movement events
            return {"PASS_THROUGH"}

        if event.type in {"ESC", "RIGHTMOUSE"}:
            return {"CANCELLED"}
        elif event.type == "LEFTMOUSE" and event.value == "RELEASE":
            if context.window_manager.dialog_properties.is_property_set("clicked"):
                if context.window_manager.dialog_properties.clicked == "OK":
                    return {"FINISHED"}
                elif context.window_manager.dialog_properties.clicked == "CANCEL":
                    return {"CANCELLED"}

        return {"RUNNING_MODAL"}

    def draw(self, context):
        u.draw_objects_sets_uilist(self.layout, context)


class SimpleToolbox_OT_AddObjectSetPopup(bpy.types.Operator):
    bl_label = "Add Object Set"
    bl_idname = "r0tools.add_object_set_popup"
    bl_description = "Add a new Object Set Entry"
    bl_options = {"REGISTER", "UNDO"}

    _default_name = "New Set"
    _default_colour = (0.0, 0.0, 0.0, 1.0)
    separator: BoolProperty(default=False)  # type: ignore
    object_set_name: StringProperty(name="Set Name", default=_default_name)  # type: ignore
    object_set_colour: FloatVectorProperty(  # type: ignore
        name="Object Set Colour",
        subtype="COLOR",
        size=4,  # RGBA
        min=0.0,
        max=1.0,
        default=_default_colour,
    )

    @classmethod
    def poll(cls, context):
        return context.mode == u.OBJECT_MODES.OBJECT

    def invoke(self, context, event):
        # Reset Name
        self.object_set_name = self._default_name

        # Reset Colour
        self._default_colour = u.get_addon_prefs().object_sets_default_colour
        self.object_set_colour = self._default_colour

        # Reset is separator
        self.separator = False

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        addon_prefs = u.get_addon_prefs()
        addon_object_sets_props = u.get_addon_object_sets_props()

        label_add_new = "Create a New Object Set"
        if self.separator:
            label_add_new = "Add new Separator"

        layout = self.layout
        layout.label(text=label_add_new, icon="ADD")

        separator_checkbox_row = layout.row()
        separator_checkbox_row.prop(self, "separator", text="Separator?")

        if self.separator:
            return

        row = layout.row()
        split = row.split(factor=0.9)
        split.prop(self, "object_set_name")
        if addon_object_sets_props.object_sets_use_colour:
            split.prop(self, "object_set_colour", text="")

    def add_non_conflicting_name(self) -> str:
        addon_object_sets_props = u.get_addon_object_sets_props()
        existing_names = [object_set.name for object_set in addon_object_sets_props.object_sets]

        if self.object_set_name not in existing_names:
            return self.object_set_name

        # Base name without suffix
        base_prefix = self.object_set_name.split(".")[0]

        # Collect all existing suffixes for this base name
        used_suffixes = set()
        for name in existing_names:
            if name.startswith(base_prefix):
                # Try to extract the numerical suffix
                parts = name.split(".")
                if len(parts) > 1:
                    try:
                        suffix = int(parts[-1])
                        used_suffixes.add(suffix)
                    except ValueError:
                        # Ignore names without valid numerical suffixes
                        pass

        # Lowest available suffix
        suffix = 1
        while suffix in used_suffixes:
            suffix += 1

        return f"{self.object_set_name}.{suffix:03}"

    def execute(self, context):
        if self.separator:
            new_set = u.get_object_sets().add()
            new_set.name = new_set.default_separator_name
            new_set.separator = self.separator

            self.report({"INFO"}, f"Added separator ot Object Sets")
        else:
            new_set = u.get_object_sets().add()
            new_set.name = self.add_non_conflicting_name()
            new_set.set_object_set_colour(self.object_set_colour)
            set_active_object_set_index(len(u.get_object_sets()) - 1)

            # Immediately add selected objects to set, for convenience
            if context.selected_objects:
                bpy.ops.r0tools.assign_to_object_set()

            self.report(
                {"INFO"}, f"Created Object Set: {self.object_set_name} with colour: {self.object_set_colour[:]}"
            )

        if context.area:
            context.area.tag_redraw()

        return {"FINISHED"}


class SimpleToolbox_OT_RemoveObjectSet(bpy.types.Operator):
    bl_label = "Remove Object Set"
    bl_idname = "r0tools.remove_object_set"
    bl_description = "Remove the selected Object Set entry"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == u.OBJECT_MODES.OBJECT and len(u.get_object_sets()) > 0

    def execute(self, context):
        index = get_active_object_set_index()

        if 0 <= index < get_object_sets_count():
            set_name = get_object_set_name_at_index(index)
            remove_object_set_at_index(index)
            set_active_object_set_index(max(0, index - 1))
            self.report({"INFO"}, f"Removed Object Set: {set_name}")
        return {"FINISHED"}


class SimpleToolbox_OT_RenameObjectSet(bpy.types.Operator):
    bl_label = "Rename"
    bl_idname = "r0tools.rename_object_set"
    bl_description = "Rename the selected Object Set entry"

    new_name: StringProperty(name="New Object Set Name", default="")  # type: ignore

    def invoke(self, context, event):
        index = get_active_object_set_index()

        if 0 <= index < get_object_sets_count():
            object_set = get_object_set_at_index(index)
            self.new_name = object_set.name

        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        index = get_active_object_set_index()

        if 0 <= index < get_object_sets_count():
            object_set = get_object_set_at_index(index)
            old_name = object_set.name
            success = set_object_set_name(object_set, self.new_name)
            if success:
                self.report({"INFO"}, f"Renamed '{old_name}' to '{self.new_name}'")

        return {"FINISHED"}


class SimpleToolbox_OT_MoveObjectSetItem(bpy.types.Operator):
    bl_label = "Move Object Set"
    bl_idname = "r0tools.objet_set_item_move"
    bl_description = "Move the selected Object Set up or down.\n\nMODIFIERS:\n- SHIFT: Move to Top/Bottom"
    bl_options = {"INTERNAL"}

    absolute: BoolProperty(default=False)  # type: ignore
    direction: bpy.props.StringProperty(default="")  # type: ignore

    def invoke(self, context, event):
        self.absolute = False  # Always reset

        if event.shift:
            self.absolute = True

        return self.execute(context)

    def execute(self, context):
        active_index = get_active_object_set_index()
        object_sets = get_object_sets()
        # separator = get_object_set_at_index(active_index).separator

        to_index = active_index

        if self.direction == "UP":
            if active_index > 0:
                if self.absolute:
                    to_index = 0  # All the way up
                else:
                    to_index = active_index - 1

        elif self.direction == "DOWN":
            if active_index < len(object_sets) - 1:
                if self.absolute:
                    to_index = len(object_sets) - 1  # All the way down
                else:
                    to_index = active_index + 1

        move_object_set_to_index(active_index, to_index)
        set_active_object_set_index(to_index)

        # Deprecated, we don't actually need to update the count
        # making it incredibly faster to move up and down especially
        # when having Sets with large amounts of objects

        # if not separator:
        # object_set_at_index_update_count(active_index)
        # object_set_at_index_update_count(to_index)

        return {"FINISHED"}


class SimpleToolbox_OT_AddToObjectSet(bpy.types.Operator):
    bl_label = "Assign"
    bl_idname = "r0tools.assign_to_object_set"
    bl_description = "Add selected objects to selected Object Set Entry"
    bl_options = {"INTERNAL"}

    accepted_contexts = [u.OBJECT_MODES.OBJECT]

    @classmethod
    def poll(cls, context):
        object_sets = get_object_sets()
        active_index = get_active_object_set_index()

        # Evaluate polls
        accepted_contexts = context.mode in cls.accepted_contexts
        len_selected_objects = len(context.selected_objects) > 0
        is_separator = object_sets[active_index].separator if len(object_sets) else False

        return accepted_contexts and len_selected_objects and not is_separator

    def execute(self, context):
        index = get_active_object_set_index()

        if 0 <= index < get_object_sets_count():
            object_set = get_object_set_at_index(index)
            object_set_count_before = object_set.count

            object_set.assign_objects(context.selected_objects)

            object_set_count_after = object_set.count - object_set_count_before

            u.timer_manager.schedule(object_sets_update_mesh_stats, delay=1, min_interval=1)

            self.report(
                {"INFO"},
                f"Added {object_set_count_after} object(s) to Set '{object_set.name}'",
            )
        return {"FINISHED"}


class SimpleToolbox_OT_RemoveFromObjectSet(bpy.types.Operator):
    bl_label = "Remove"
    bl_idname = "r0tools.remove_from_object_set"
    bl_description = "Remove selected objects from selected Object Set entry"
    bl_options = {"INTERNAL"}

    accepted_contexts = [u.OBJECT_MODES.OBJECT]

    @classmethod
    def poll(cls, context):
        object_sets = get_object_sets()
        active_index = get_active_object_set_index()

        # Evaluate polls
        accepted_contexts = context.mode in cls.accepted_contexts
        len_selected_objects = len(context.selected_objects) > 0
        is_separator = get_object_set_at_index(active_index).separator if len(object_sets) else False

        return accepted_contexts and len_selected_objects and not is_separator

    def execute(self, context):
        index = get_active_object_set_index()

        if 0 <= index < get_object_sets_count():
            object_set = get_object_set_at_index(index)

            initial_count = len(object_set.objects)
            object_set.remove_objects(context.selected_objects)
            total_removed = initial_count - len(object_set.objects)

            self.report({"INFO"}, f"Removed {total_removed} objects of Set '{object_set.name}'")

        u.timer_manager.schedule(object_sets_update_mesh_stats, delay=1, min_interval=1)

        return {"FINISHED"}


class SimpleToolbox_OT_RemoveFromAllObjectSets(bpy.types.Operator):
    bl_label = "Remove From All Sets"
    bl_idname = "r0tools.remove_from_all_object_sets"
    bl_description = "Remove selected object(s) from all Object Sets"
    bl_options = {"INTERNAL"}

    accepted_contexts = [u.OBJECT_MODES.OBJECT]

    @classmethod
    def poll(cls, context):
        object_sets = get_object_sets()

        # Evaluate polls
        accepted_contexts = context.mode in cls.accepted_contexts
        object_sets_present = True if len(object_sets) > 0 else False
        len_selected_objects = len(context.selected_objects) > 0

        return accepted_contexts and len_selected_objects and object_sets_present

    def execute(self, context):
        object_sets = get_object_sets()

        for object_set in object_sets:
            object_set.remove_objects(context.selected_objects)

        self.report({"INFO"}, f"Removed selected objects from all Object Sets")

        u.timer_manager.schedule(object_sets_update_mesh_stats, delay=1, min_interval=1)

        return {"FINISHED"}


class SimpleToolbox_OT_SelectObjectSet(bpy.types.Operator):
    bl_label = "Select"
    bl_idname = "r0tools.select_object_set"
    bl_description = "SHIFT: Add to Selection"
    bl_options = {"INTERNAL"}

    add_to_selection = False
    set_index: IntProperty(default=-1)  # type: ignore

    accepted_contexts = accepted_contexts = [u.OBJECT_MODES.OBJECT]

    @classmethod
    def poll(cls, context):
        accepted_contexts = context.mode in cls.accepted_contexts
        return accepted_contexts

    def invoke(self, context, event):
        self.add_to_selection = False  # Always reset

        if event.shift:
            self.add_to_selection = True

        return self.execute(context)

    def execute(self, context):
        if self.set_index < 0:
            index = get_active_object_set_index()
        else:
            index = self.set_index

        if 0 <= index < get_object_sets_count():
            object_set = get_object_set_at_index(index)

            # If separator or no objects in the set, don't do anything
            if object_set.separator or object_set.count < 1:
                return {"FINISHED"}

            if u.IS_DEBUG():
                print(f"[DEBUG] [{_mod}] {self.add_to_selection=}")

            if not self.add_to_selection:
                u.deselect_all()

            to_become_active = object_set.objects[0].object
            for object_set_item in reversed(object_set.objects):
                obj = object_set_item.object
                u.select_object(obj)

            u.set_active_object(to_become_active)

            self.report({"INFO"}, f"Selected objects in '{object_set.name}'")
        return {"FINISHED"}


class SimpleToolbox_OT_ForceRefreshObjectSets(bpy.types.Operator):
    """Force run update count which should help refresh some Object Sets properties"""

    bl_label = "Force Refresh Sets Colours"
    bl_idname = "r0tools.object_sets_refresh"
    bl_description = "Force refresh and update Object Sets' colours"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        addon_prefs = u.get_addon_prefs()
        addon_object_sets_props = u.get_addon_object_sets_props()

        if addon_object_sets_props.object_sets_use_colour:
            u.refresh_object_sets_colours(context)

            self.report({"INFO"}, f"Refreshed Object Sets' colours")

        return {"FINISHED"}


class SimpleToolbox_OT_RandomiseObjectSetsColours(bpy.types.Operator):
    """
    Randomise the colour of each Object Set, respecting the existing colours (if any) and without overlapping colours
    """

    bl_label = "Randomise"
    bl_idname = "r0tools.object_sets_colours_randomise"
    bl_description = "Randomise the colour of each Object Set, respecting the existing colours (if any) and without overlapping colours.\n\nMODIFIERS:\n- SHIFT: Force randomise all Object Sets' colours\n- CTRL: Force randomise active Object Set colour"
    bl_options = {"INTERNAL", "UNDO"}

    override = False
    override_active = False

    def invoke(self, context, event):
        self.override = False  # Always reset
        self.override_active = False  # Always reset

        if event.shift:
            self.override = True
        elif event.ctrl:
            self.override_active = True

        return self.execute(context)

    def execute(self, context):
        addon_prefs = u.get_addon_prefs()
        default_set_colour = [c for c in addon_prefs.object_sets_default_colour]
        used_colours = {tuple(o.set_colour) for o in get_object_sets() if list(o.set_colour) != default_set_colour}
        active_object_set_name = get_object_set_name_at_index(get_active_object_set_index())

        for object_set in get_object_sets():
            if object_set.separator:
                continue

            should_change_color = False
            current_color_is_default = [c for c in object_set.set_colour] == default_set_colour
            object_set_name = object_set.name
            is_active_set = object_set_name == active_object_set_name

            if self.override:
                # Force override all Object Sets' colours
                should_change_color = True
            elif self.override_active and is_active_set:
                # Force override only the active Object Set colour
                should_change_color = True
            elif current_color_is_default and not self.override_active:
                # Randomise colour of Object Set if the colour is default and we're not specifically overriding anything
                should_change_color = True

            if should_change_color:
                for _ in range(10):  # While loops can go wrong. Range is more controlled. Boom!
                    new_colour = (
                        random.uniform(0.0, 1.0),
                        random.uniform(0.0, 1.0),
                        random.uniform(0.0, 1.0),
                        1.0,
                    )

                    is_similar = False
                    for col in used_colours:
                        if self.is_colour_similar(new_colour, col, threshold=0.15):
                            is_similar = True
                            break

                    # Check against default colour. Stricter.
                    if self.is_colour_similar(new_colour, tuple(default_set_colour), threshold=0.4):
                        is_similar = True

                    if not is_similar:
                        used_colours.add(new_colour)
                        object_set.set_colour = new_colour
                        u.LOG(f"[INFO] [{_mod}] Updating colour of Object Set '{object_set_name}': {new_colour}")
                        break

        bpy.ops.r0tools.object_sets_refresh()
        self.report({"INFO"}, "Randomised Object Sets' Colours.")
        return {"FINISHED"}

    def is_colour_similar(self, new_colour, colour_to_compare_to, threshold=0.1):
        """Check if two colors are similar within a given threshold using weighted Euclidean distance.

        The weighted is tailored to better match the human perception element: Red 30%, Green 59%, Blue 11%

        Threshold of 0: mostly only exact matches are considered similar.

        Threshold of 1.0: all colour(s) can be considered similar.
        """

        # Perception-based weights (these should sum to 1.0 for consistent scaling)
        weight_red = 0.30
        weight_green = 0.59
        weight_blue = 0.11

        # The maximum possible distance between two unweighted colors in RGB space is √3 ≈ 1.73

        max_distance = (weight_red + weight_green + weight_blue) ** 0.5

        if threshold > 1:
            mapped_threshold = max_distance
        elif threshold < 0:
            mapped_threshold = 0
        else:
            # Under normal conditions, from 0-1.0, map according to the RGB scale
            mapped_threshold = threshold * max_distance

        r1, g1, b1 = new_colour[:3]
        r2, g2, b2 = colour_to_compare_to[:3]

        # Calculate weighted squared differences
        r_diff_squared = weight_red * ((r1 - r2) ** 2)
        g_diff_squared = weight_green * ((g1 - g2) ** 2)
        b_diff_squared = weight_blue * ((b1 - b2) ** 2)

        distance = (r_diff_squared + g_diff_squared + b_diff_squared) ** 0.5

        is_similar = distance < mapped_threshold

        if is_similar:
            # `distance` means a difference of X%.
            # A distance of 0.313, means that `new_colour` is only 31.3% different than `color_to_compare_to`.
            # So they are 68.7% similar.
            similar_pct = (1 - distance / max_distance) * 100
            u.LOG(
                f"[INFO] [{_mod}] Color {new_colour} is {similar_pct:.1f}% similar to {colour_to_compare_to} with distance of {distance:.3f} | ({mapped_threshold:.3f})"
            )

        return is_similar


class SimpleToolbox_OT_RenameObjectsInObjectSet(bpy.types.Operator):
    """
    Rename Objects of selected Object Set to share the same name as the Set they are contained in.
    """

    bl_label = "Rename Objects in Selected Set"
    bl_idname = "r0tools.object_sets_rename_objects_in_set"
    bl_description = 'Renames Objects in the selected Object Set (Highlighted in the Set List) to take the name of the Object Set they belong to.\n\nExample:\nAn Object Set named "Example Set" will have objects associated to itself renamed to "Example Set", "Example Set.001", "Example Set.002", etc.'
    bl_options = {"INTERNAL", "UNDO"}

    @classmethod
    def poll(cls, context):
        return get_object_sets_count() > 0

    def execute(self, context):
        active_index = get_active_object_set_index()
        active_object_set_name = get_object_set_name_at_index(active_index)

        renamed_count = 0

        # This does not account for instances of existing or similar object set names

        for obj in iter_objects_of_object_set_at_index(active_index):
            if not obj:
                # Sometimes, the reference can be NoneType.
                continue
            obj.name = active_object_set_name
            renamed_count += 1

        self.report({"INFO"}, f"Renamed {renamed_count} objects to {active_object_set_name}")
        return {"FINISHED"}


class SimpleToolbox_OT_MoveObjectsInObjectSetsToCollections(bpy.types.Operator):
    """
    Moves objects in selected Object Set into collections named as the Set they are contained in.
    """

    bl_label = "Move to collections"
    bl_idname = "r0tools.move_objects_in_set_into_collections"
    bl_description = "Moves Objects in the selected Object Set (Highlighted in the Set List) into a collection that is named the same as the set they are contained in.\n\nMODIFIERS:\n- SHIFT: Apply this logic to ALL Object Sets"
    bl_options = {"INTERNAL", "UNDO"}

    do_all = False

    @classmethod
    def poll(cls, context):
        return get_object_sets_count() > 0

    def invoke(self, context, event):
        self.do_all = False  # Always reset

        if event.shift:
            self.do_all = True

        return self.execute(context)

    def execute(self, context):
        import random

        if u.IS_DEBUG():
            print("\n------------- Move Objects In Object Sets Into Set Collections -------------")

        active_index = get_active_object_set_index()
        active_name = get_object_set_name_at_index(active_index)
        collections = []

        if not self.do_all:
            collection = u.collections_create_new(active_name)
            # Append newly or referenced collection.
            collections.append(collection)

            if not collection:
                return {"CANCELLED"}

            for obj in iter_objects_of_object_set_at_index(active_index):
                u.collection_link_object(collection, obj, unlink_others=True)
        else:
            i = get_object_sets_count()
            for object_set in reversed(get_object_sets()):
                i -= 1
                u.LOG(f"[INFO] [{_mod}] {i} {object_set.name}")
                if object_set.separator:
                    continue
                collection = u.collections_create_new(get_object_set_name_at_index(i))
                # Append newly or referenced collection.
                collections.append(collection)

                for obj in iter_objects_of_object_set_at_index(i):
                    u.collection_link_object(collection, obj, unlink_others=True)

        # Delete empty collections for tidiness
        # Sometimes it can be that objects are created in one collection and
        # moved to another if they belong to another Object Set, which means
        # they can shift collections as they are added from bottom to top.

        # Also apply colours here while we're at it (iterating over collections)
        colours = u.COLLECTION_COLOURS.values()
        applied_colours: list[str] = []
        for coll in reversed(collections):
            if len(coll.objects) < 1:
                u.remove_collection(coll)
                collections.remove(coll)
            else:
                # Reset applied if full
                if len(applied_colours) >= len(colours):
                    applied_colours.clear()

                # Apply colour
                colour = random.choice(colours)
                if colour in applied_colours:
                    for i in range(10):
                        colour = random.choice(colours)
                        if colour not in applied_colours:
                            break

                u.collection_set_colour(coll, colour)
                if colour not in applied_colours:
                    applied_colours.append(colour)

        return {"FINISHED"}


class SimpleToolbox_OT_LinkObjectsInObjectSetsToCollections(bpy.types.Operator):
    """
    Links objects in selected Object Set into collections named as the Set they are contained in.
    """

    bl_label = "Link to collections"
    bl_idname = "r0tools.link_objects_in_set_to_collections"
    bl_description = "Links Objects in the selected Object Set (Highlighted in the Set List) into a collection that is named the same as the set they are contained in.\n\nMODIFIERS:\n- CTRL: Unlink from other collections (Can act as cleanup)\n- SHIFT: Apply this logic to ALL Object Sets"
    bl_options = {"INTERNAL", "UNDO"}

    do_all = False
    unlink_from_others = False

    @classmethod
    def poll(cls, context):
        return get_object_sets_count() > 0

    def invoke(self, context, event):
        self.do_all = False  # Always reset
        self.unlink_from_others = False  # Always reset

        if event.ctrl:
            self.unlink_from_others = True

        if event.shift:
            self.do_all = True

        return self.execute(context)

    def execute(self, context):
        import random

        if u.IS_DEBUG():
            print("\n------------- Link Objects In Object Sets To Set Collections -------------")

        active_index = get_active_object_set_index()
        active_name = get_object_set_name_at_index(active_index)
        collections = []

        if not self.do_all:
            collection = u.collections_create_new(active_name)
            # Append newly or referenced collection.
            collections.append(collection)

            if not collection:
                return {"CANCELLED"}

            for obj in iter_objects_of_object_set_at_index(active_index):
                u.collection_link_object(collection, obj, unlink_others=self.unlink_from_others)
        else:
            i = get_object_sets_count()
            for object_set in reversed(get_object_sets()):
                i -= 1
                u.LOG(f"[INFO] [{_mod}] {i} {object_set}.name")
                if object_set.separator:
                    continue
                collection = u.collections_create_new(get_object_set_name_at_index(i))
                # Append newly or referenced collection.
                collections.append(collection)

                for obj in iter_objects_of_object_set_at_index(i):
                    u.collection_link_object(collection, obj, unlink_others=self.unlink_from_others)

        # Delete empty collections for tidiness
        # Sometimes it can be that objects are created in one collection and
        # moved to another if they belong to another Object Set, which means
        # they can shift collections as they are added from bottom to top.

        # Also apply colours here while we're at it (iterating over collections)
        colours = u.COLLECTION_COLOURS.values()
        applied_colours: list[str] = []
        for coll in reversed(collections):
            if len(coll.objects) < 1:
                u.remove_collection(coll)
                collections.remove(coll)
            else:
                # Reset applied if full
                if len(applied_colours) >= len(colours):
                    applied_colours.clear()

                # Apply colour
                colour = random.choice(colours)
                if colour in applied_colours:
                    for i in range(10):
                        colour = random.choice(colours)
                        if colour not in applied_colours:
                            break

                u.collection_set_colour(coll, colour)
                if colour not in applied_colours:
                    applied_colours.append(colour)

        return {"FINISHED"}


# ===================================================================
#   Register & Unregister
# ===================================================================

# fmt: off
classes = [
    SimpleToolbox_OT_ObjectSetsModal,
    SimpleToolbox_OT_AddObjectSetPopup,
    SimpleToolbox_OT_RenameObjectSet,
    SimpleToolbox_OT_MoveObjectSetItem,
    SimpleToolbox_OT_RemoveObjectSet,
    SimpleToolbox_OT_AddToObjectSet,
    SimpleToolbox_OT_RemoveFromObjectSet,
    SimpleToolbox_OT_RemoveFromAllObjectSets,
    SimpleToolbox_OT_SelectObjectSet,
    SimpleToolbox_OT_ForceRefreshObjectSets,
    SimpleToolbox_OT_RandomiseObjectSetsColours,
    SimpleToolbox_OT_RenameObjectsInObjectSet,
    SimpleToolbox_OT_MoveObjectsInObjectSetsToCollections,
    SimpleToolbox_OT_LinkObjectsInObjectSetsToCollections,
]
# fmt: on


def object_sets_modal_menu_func(self, context):
    self.layout.operator(SimpleToolbox_OT_ObjectSetsModal.bl_idname)


def register():
    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    # Register Objects Sets Modal Operator in Viewport > View
    bpy.types.VIEW3D_MT_view.append(object_sets_modal_menu_func)

    # Register Objects Sets Modal Operator in Image Editor/UV > View
    bpy.types.IMAGE_MT_view.append(object_sets_modal_menu_func)


def unregister():
    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)

    # Unregister Objects Sets Modal Operator in Viewport > View
    bpy.types.VIEW3D_MT_view.remove(object_sets_modal_menu_func)

    # Unregister Objects Sets Modal Operator in Image Editor/UV > View
    bpy.types.IMAGE_MT_view.remove(object_sets_modal_menu_func)
