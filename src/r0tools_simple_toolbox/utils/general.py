import logging
import math
import uuid
from contextlib import contextmanager
from pathlib import Path

import bmesh
import bpy

from .. import utils as u

log = logging.getLogger(__name__)


def get_file_version() -> tuple[int, int, int]:
    return bpy.data.version


def get_blender_version() -> tuple[int, int, int]:
    return bpy.app.version


def generate_uuid() -> str:
    return str(uuid.uuid4())


def get_bl_config_path() -> str:
    script_paths_user = bpy.utils.script_path_user()
    if not Path(script_paths_user).exists():
        return ""

    config_folder = Path(script_paths_user).parent

    return str(config_folder)


# ==============================
# OBJECT, MESH, SELECTION
# ==============================


def set_active_object(obj: bpy.types.Object):
    """Set the active object in the current view layer"""
    objects = getattr(bpy.context.view_layer, "objects", None)

    if objects and is_valid_object_global(obj) and is_object_visible_in_viewport(obj):
        bpy.context.view_layer.objects.active = obj


def get_active_object() -> bpy.types.Object | None:
    """Get the active object from the current view layer"""
    objects = getattr(bpy.context.view_layer, "objects", None)

    if objects:
        return getattr(objects, "active", None)

    # return bpy.context.view_layer.objects.active
    return None


def get_selected_objects(context: bpy.types.Context | None = None) -> list:
    if context is not None:
        return context.selected_objects

    if hasattr(bpy.context, "selected_objects"):
        return bpy.context.selected_objects

    return []


def set_object_mode(mode: str):
    """
    Set the current object mode

    - OBJECT
    - EDIT (EDIT_MESH)
    - SCULPT
    - VERTEX_PAINT
    - TEXTURE_PAINT
    - WEIGHT_PAINT

    Args:
        mode: One of the modes defined in `OBJECT_MODES`
    """
    log.debug(f"Setting mode: {mode}")

    # Edit Mode weirdness fix
    if mode.upper() == "EDIT_MESH":
        mode = u.OBJECT_MODES.EDIT
    bpy.ops.object.mode_set(mode=mode)


def set_mode_object():
    """Sets the current mode to Object Mode"""
    set_object_mode("OBJECT")


def set_mode_edit():
    """Sets the current mode to Edit Mode"""
    set_object_mode("EDIT")


def select_object(obj: bpy.types.Object, add=True, set_active=False) -> bpy.types.Object | None:
    """
    Select an object in the scene

    Args:
        obj: Object to select
        add: Whether to add to current selection or replace it
        set_active: Whether to set this as the active object

    Returns:
        The selected object or None if failed
    """
    log.debug(f"Selecting {obj.name} {add=} {set_active=}")

    if not add:
        deselect_all()

    if not is_valid_object_global(obj):
        return None

    if not is_object_visible_in_viewport(obj):
        return None

    try:
        obj.select_set(True)
    except Exception as e:
        log.error(f"Selecting {obj.name} {e}")

    if not add or set_active:
        set_active_object(obj)

    return obj


def deselect_object(obj: bpy.types.Object) -> bpy.types.Object | None:
    """
    Deselect an object in the scene

    Args:
        obj: Object to deselect

    Returns:
        The deselected object or None if failed
    """
    log.debug(f"Deselecting {obj.name}")

    if not is_valid_object_global(obj):
        return None

    try:
        obj.select_set(False)
    except Exception as e:
        log.error(f"Deselecting {obj.name} {e}")

    return obj


def is_object_visible_in_viewport(obj):
    """
    Check if an object is visible in the viewport

    This checks both the object's visibility setting and
    whether its collections are visible
    """
    # Check if the object is set to be visible in the viewport
    if not obj.visible_get():
        log.debug(f"{obj.name} is not visible in viewport.")
        return False

    log.debug(f"{obj.name} is visible in viewport.")
    log.debug(f"Checking {obj.name} Collection(s).")

    # Check if the object's collection is visible in the viewport
    for collection in obj.users_collection:
        log.debug(f"   - {collection.name}")
        if not collection.hide_viewport:
            log.debug(f"   - {collection.name} is visible.")
            return True
        else:
            log.debug(f"   - {collection.name} is hidden.")

    return False


def unhide_object_and_collections(obj: bpy.types.Object):
    """
    Recursively unhide object and all it's parent collections.

    Returns a list of items that were modified, for later restoration if needed.

    Returns:
        list: List of tuples (item, attr_name, original_value)
    """

    modified = []

    # Get the view layer
    view_layer = bpy.context.view_layer

    # Check Object.hide_viewport (monitor icon)
    # NOTE: Will skip for now, as should be controlled by
    # a Property, such as "force_unhide_objects" so that
    # the user can still retain objects in object sets
    # but hide then using the monitor icon - more deliberately
    # to have finer control over what is exported
    has_implemented_feature = False
    if has_implemented_feature:
        if obj.hide_viewport:
            modified.append((obj, "hide_viewport", True))
            obj.hide_viewport = False

    # Check object's visibility (eye icon)
    if obj.hide_get():
        modified.append((obj, "hide_set", True))
        obj.hide_set(False)

    # Check Object's selectability
    if obj.hide_select:
        modified.append((obj, "hide_select", True))
        obj.hide_select = False

    # Helper to find LayerCollection for a given Collection
    def find_layer_collection(layer_collection, collection):
        if layer_collection.collection == collection:
            return layer_collection

        for child in layer_collection.children:
            result = find_layer_collection(child, collection)
            if result:
                return result
        return None

    # Recursively unhide parent collections
    def unhide_collection_hierarchy(collection):
        # Check Collection's selectability
        if collection.hide_select:
            modified.append((collection, "hide_select", True))
            collection.hide_select = False

        # Check Collection.hide_viewport attribute (monitor icon)
        if collection.hide_viewport:
            modified.append((collection, "hide_viewport", True))
            collection.hide_viewport = False

        layer_collection = find_layer_collection(view_layer.layer_collection, collection)

        if layer_collection and layer_collection.hide_viewport:
            modified.append((layer_collection, "hide_viewport", True))
            layer_collection.hide_viewport = False

        # Check parents
        for parent_coll in bpy.data.collections:
            if collection.name in parent_coll.children:
                unhide_collection_hierarchy(parent_coll)

    # Unhide all collections
    for collection in obj.users_collection:
        unhide_collection_hierarchy(collection)

    return modified


def restore_visibility_state(modified):
    """
    Restore the original visibility state of objects and collections
    given a modifications list.
    """

    for item, attr_name, original_value in modified:
        if attr_name == "hide_set":
            item.hide_set(original_value)
        else:
            setattr(item, attr_name, original_value)


# Context manager for unhiding and restoring object and collection visibility
@contextmanager
def temporarily_unhide_objects(objects: list | tuple | set):
    """
    Context manager to temporarily unhide objects and their collections,
    ending by restorign their state before change.
    """

    all_modified = []

    try:
        for obj in objects:
            modified = unhide_object_and_collections(obj)
            all_modified.extend(modified)

        yield  # Allow operations here

    finally:
        restore_visibility_state(all_modified)


def deselect_all():
    """Deselect all objects or elements based on current mode"""
    context_mode = bpy.context.mode
    edit_modes = [u.OBJECT_MODES.EDIT, u.OBJECT_MODES.EDIT_MODE]
    object_modes = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.OBJECT_MODE]

    if context_mode in edit_modes:
        bpy.ops.mesh.select_all(action="DESELECT")
    elif context_mode in object_modes:
        bpy.ops.object.select_all(action="DESELECT")


def deselect_all_bmesh(bmesh_obj):
    # Deselect all elements
    for vert in bmesh_obj.verts:
        vert.select = False
    for edge in bmesh_obj.edges:
        edge.select = False
    for face in bmesh_obj.faces:
        face.select = False


def bmesh_get_crease_layer(bm):
    return bm.edges.layers.float.get("crease_edge", None)


def bmesh_new_crease_layer(bm):
    bm.edges.layers.float.new("crease_edge")

    return bmesh_get_crease_layer(bm)


def bmesh_get_bevel_weight_edge_layer(bm):
    return bm.edges.layers.float.get("bevel_weight_edge", None)


def bmesh_new_bevel_weight_edge_layer(bm):
    bm.edges.layers.float.new("bevel_weight_edge")

    return bmesh_get_bevel_weight_edge_layer(bm)


def object_in_view_layer(obj, context=None):
    """Check if object is in the active view layer"""
    ctx = bpy.context
    if context:
        ctx = context

    return obj.visible_get(view_layer=ctx.view_layer)


def object_visible(obj):
    """Check if object is visible"""
    return obj.visible_get()


def is_valid_object_global(obj):
    """
    Check if an object reference is valid
    """
    try:
        if not obj:
            return False

        if obj.as_pointer == 0:
            return False

        # Direct data check
        data_objects = bpy.data.objects
        if obj.name not in data_objects:
            return False

        # Has the object been orphaned?
        return any(data_objects[obj.name].users_scene)
    except (ReferenceError, KeyError):
        return False
    except Exception as e:
        log.error(f"Validation error: {e}")
        return False


def iter_scene_objects(selected=False, types: list[str] = []):
    """
    Iterate through objects in the scene

    Args:
        selected: Only iterate through selected objects
        types: Filter by object types (empty list = all types)
    """

    if selected:
        iters = get_selected_objects()
    else:
        iters = bpy.data.objects

    for o in iters:
        if not types or o.type in types:
            yield o


def iter_data_objects(types: list[str] = []):
    """
    Iterate through objects in bpy.data.objects

    Args:
        types: Filter by object types (empty list = all types)
    """
    for o in bpy.data.objects:
        if not types or o.type in types:
            yield o


def iter_obj_children(p_obj, recursive=True):
    """
    Iterate through all children of a given parent object

    Args:
        p_obj: Parent object to find children for
        recursive: If True, also iterate through children of children
    """
    for obj in bpy.data.objects:
        if obj.parent == p_obj:
            yield obj
            if recursive:
                yield from iter_obj_children(obj, recursive=True)


def collection_exists(name: str, is_global: bool = False) -> bool:
    if is_global:
        return name in bpy.data.collections

    return name in bpy.context.scene.collection.children.keys()


def collections_create_new(name: str):
    if not collection_exists(name):
        collection = bpy.data.collections.new(name=name)

        # Link to scene
        bpy.context.scene.collection.children.link(collection)
    else:
        collection = bpy.context.scene.collection.children.get(name, None)

    return collection


def collection_link_object(collection, obj, unlink_others: bool = False):
    # Sometimes, the reference can be NoneType.
    if not obj:
        return False

    if unlink_others:
        for coll in bpy.data.collections:
            if obj.name in coll.objects:
                coll.objects.unlink(obj)

    # Loop for user collections that object is linked to
    if unlink_others:
        for coll in obj.users_collection:
            coll.objects.unlink(obj)

    # Test if object is in the collection already
    if not object_in_collection(obj, collection):
        collection.objects.link(obj)

    return True

    return True


def remove_collection(collection):
    bpy.data.collections.remove(collection)


def collection_exists(name: str, is_global: bool = False) -> bool:
    if is_global:
        return name in bpy.data.collections

    return name in bpy.context.scene.collection.children.keys()


def collections_create_new(name: str):
    if not collection_exists(name):
        collection = bpy.data.collections.new(name=name)

        # Link to scene
        bpy.context.scene.collection.children.link(collection)
    else:
        collection = bpy.context.scene.collection.children.get(name, None)

    return collection


def collection_set_colour(collection, colour: str):
    collection.color_tag = colour


def object_in_collection(obj, collection):
    if not collection:
        return False

    return collection in obj.users_collection


def get_selected_objects_hash():
    """Generate hash to detect selection changes"""
    selected = list(iter_scene_objects(selected=True))

    if not selected:
        return 0

    # Use pointers (memory addresses) for unique id'ing
    # Sort pointer to ensure consistent order
    pointers = tuple(sorted(obj.as_pointer() for obj in selected))

    return hash(pointers)


# ==============================
# MESH SELECTION MODE
# ==============================


def _set_mesh_selection_mode(use_extend=False, use_expand=False, type=""):
    """Base function for setting mesh selection mode"""
    bpy.ops.mesh.select_mode(use_extend=use_extend, use_expand=use_expand, type=type)


def set_mesh_selection_vertex(*args, **kwargs):
    """Set selection mode to Vertex"""
    kwargs["type"] = "VERT"
    _set_mesh_selection_mode(*args, **kwargs)


def set_mesh_selection_edge(*args, **kwargs):
    """Set selection mode to Edge"""
    kwargs["type"] = "EDGE"
    _set_mesh_selection_mode(*args, **kwargs)


def set_mesh_selection_face(*args, **kwargs):
    """Set selection mode to Face"""
    kwargs["type"] = "FACE"
    _set_mesh_selection_mode(*args, **kwargs)


# ==============================
# UI & NOTIFICATIONS
# ==============================


def show_notification(message, title="Operation Complete"):
    """Display a popup notification and status info message"""
    bpy.context.window_manager.popup_menu(lambda self, context: self.layout.label(text=message), title=title)
    bpy.context.workspace.status_text_set(message)


def force_redraw_all():
    """Force a redraw of all UI areas"""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


def tag_redraw_if_visible():
    if not bpy.context.screen:
        return

    for area in bpy.context.screen.areas:
        if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
            if area.type == "PROPERTIES":
                for space in area.spaces:
                    if hasattr(space, "context") and space.context == "DATA":
                        area.tag_redraw()
                        break
            else:
                area.tag_redraw()


# ==============================
# OPERATIONS
# ==============================


def op_clear_sharp_along_axis(axis: str):
    """
    Clear sharp edges along specified axis

    Args:
        axis: The axis to clear sharp edges along (X, Y, or Z)
    """
    log.info(f"Clear Sharp Along Axis {axis}")
    axis = str(axis).upper()

    threshold = u.get_addon_prefs().clear_sharp_axis_float_prop
    log.info(f"Threshold: {threshold}")

    # Collect select objects
    objects = [obj for obj in get_selected_objects() if obj.type == "MESH"]

    log.info(f"Objects: {objects}")

    if not objects:
        return False

    for obj in objects:
        # Set the active object
        bpy.context.view_layer.objects.active = obj
        log.info(f"Iterating: {obj.name}")

        # Check the mode
        mode = obj.mode
        log.info(f"Mode: {mode}")

        # Access mesh data
        mesh = obj.data
        log.info(f"Mesh: {mesh}")

        # Store the selection mode
        # Tuple of Booleans for each of the 3 modes
        selection_mode = tuple(u.get_scene().tool_settings.mesh_select_mode)

        # Store initial selections
        # Vertices
        selected_vertices = [v.index for v in mesh.vertices if v.select]

        # Edges
        selected_edges = [e.index for e in mesh.edges if e.select]

        # Faces
        selected_faces = [f.index for f in mesh.polygons if f.select]

        # Deselect all vertices
        set_mode_edit()
        set_mesh_selection_vertex()
        deselect_all()
        set_mode_object()  # We're in Object mode so we can select stuff. Logic is weird.

        for idx, vertex in enumerate(mesh.vertices):
            if axis == "X":
                if math.isclose(vertex.co.x, 0.0, abs_tol=threshold):
                    mesh.vertices[idx].select = True

            if axis == "Y":
                if math.isclose(vertex.co.y, 0.0, abs_tol=threshold):
                    mesh.vertices[idx].select = True

            if axis == "Z":
                if math.isclose(vertex.co.z, 0.0, abs_tol=threshold):
                    mesh.vertices[idx].select = True

        # Enter Edit mode
        set_mode_edit()

        # Switch to edge mode
        set_mesh_selection_edge(use_extend=False, use_expand=False)

        # Clear the Sharp
        bpy.ops.mesh.mark_sharp(clear=True)

        # Restore the inital selections and mode
        if selection_mode[0] is True:
            set_mesh_selection_vertex()
            deselect_all()
            set_mode_object()
            for vert_idx in selected_vertices:
                mesh.vertices[vert_idx].select = True
        if selection_mode[1] is True:
            set_mesh_selection_edge()
            deselect_all()
            set_mode_object()
            for edge_idx in selected_edges:
                mesh.edges[edge_idx].select = True
        if selection_mode[2] is True:
            set_mesh_selection_face()
            deselect_all()
            set_mode_object()
            for face_idx in selected_faces:
                mesh.polygons[face_idx].select = True

        # Set back to Object mode
        set_object_mode(mode)


def _custom_properties_store_states() -> dict:
    addon_props = u.get_addon_props()

    # Store the current selection state of Custom Property List
    selection_state = {}
    for item in addon_props.custom_property_list:
        selection_state[(item.name, item.type)] = item.selected

    return selection_state


def custom_property_list_add_props(props: set | list, prop_type, selection_state: dict):
    addon_props = u.get_addon_props()

    # Populate the UIList
    for prop_name in props:
        try:
            item = addon_props.custom_property_list.add()
            item.name = prop_name
            item.type = prop_type
            # Restore selection state if it exists
            key = (prop_name, prop_type)
            if key in selection_state:
                item.selected = selection_state[key]
        except Exception as e:
            log.error(f"Error adding unique Custom Properties: {e}")
            context_error_debug(error=e)


def property_list_update(scene=None, force_run=False):
    """
    Update property list based on selected objects

    This function updates the custom property list panel
    when object selection changes.
    """

    from .context import is_writing_context_safe

    scene = u.get_scene(scene)

    if not is_writing_context_safe(scene):
        return None

    addon_props = u.get_addon_props(scene)

    if not addon_props.cat_show_custom_properties_editor and not force_run:
        # Skip update if panel is not visible
        return None

    if get_selected_objects() or force_run:
        current_selection = {obj.name for obj in iter_scene_objects(selected=True)}

        log.debug("------------- Custom Property List Update -------------")

        # Store the current selection state before clearing the list
        selection_state = _custom_properties_store_states()

        try:
            addon_props.custom_property_list.clear()
        except Exception as e:
            log.error(f"{e}")
            return None

        # Add unique custom properties to the set
        unique_object_data_props = set()
        unique_mesh_data_props = set()
        for obj in iter_scene_objects(selected=True):
            # Object Properties
            for prop_name in obj.keys():
                log.debug(f"(OP) {obj.name} - {prop_name=}")
                if not prop_name.startswith("_") and prop_name not in unique_object_data_props:
                    unique_object_data_props.add(prop_name)

            # Object Data Properties
            if obj.data and obj.type == "MESH":
                for prop_name in obj.data.keys():
                    log.debug(f"(ODP) {obj.name} - {prop_name=}")
                    if not prop_name.startswith("_") and prop_name not in unique_mesh_data_props:
                        unique_mesh_data_props.add(prop_name)

        # Populate the UIList
        # Allows it to finally be sorted!
        custom_property_list_add_props(unique_object_data_props, u.CUSTOM_PROPERTIES_TYPES.OBJECT_DATA, selection_state)
        custom_property_list_add_props(unique_mesh_data_props, u.CUSTOM_PROPERTIES_TYPES.MESH_DATA, selection_state)

        # Update the last object selection
        try:
            addon_props.last_object_selection = ",".join(current_selection)
        except Exception as e:
            context_error_debug(
                error=e,
                extra_prints=[
                    f"addon_props.last_object_selection: {addon_props.last_object_selection}",
                    f"{current_selection=}",
                ],
            )

        # Force UI update
        for area in bpy.context.screen.areas:
            if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
                area.tag_redraw()

    else:
        # Store the states even if nothing selected
        selection_state = _custom_properties_store_states()

        # Clear the property list if no objects are selected
        try:
            addon_props.custom_property_list.clear()
            log.debug(f"Cleared UIList custom_property_list")
        except Exception as e:
            log.error(f"Error clearing custom property list when no selected objects: {e}")
            context_error_debug(error=e)
        try:
            addon_props.last_object_selection = ""
            log.debug(f"Cleared property last_object_selection")
        except Exception as e:
            log.error(f"Error setting last object selection when no selected objects: {e}")
            context_error_debug(error=e)

        # Force UI update
        if bpy.context.screen:
            if hasattr(bpy.context.screen, "areas"):
                for area in bpy.context.screen.areas:
                    if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
                        area.tag_redraw()

    return None


def _object_attributes_store_states() -> dict:
    addon_props = u.get_addon_props()

    # Store the current selection state of Custom Property List
    selection_state = {}
    for item in addon_props.object_attributes_list:
        selection_state[item.name] = item.selected

    return selection_state


def object_attributes_list_add_props(attributes: set | list, selection_state: dict):
    addon_props = u.get_addon_props()

    # Populate the UIList
    for attrib_name in sorted(attributes):
        try:
            item = addon_props.object_attributes_list.add()
            item.name = attrib_name
            # Restore selection state if it exists
            key = attrib_name
            if key in selection_state:
                item.selected = selection_state[key]
        except Exception as e:
            log.error(f"Error adding unique Object Attributes: {e}")
            context_error_debug(error=e)


def object_attributes_list_update(scene=None, force_run=False):
    """
    Update Object Attribute list based on selected objects
    """

    from .context import is_writing_context_safe

    scene = u.get_scene(scene)

    if not is_writing_context_safe(scene):
        return None

    addon_prefs = u.get_addon_prefs()
    addon_props = u.get_addon_props(scene)

    log.debug("------------- Object Attibutes List Update -------------")

    if not addon_props.cat_show_custom_properties_editor and not force_run:
        # Skip update if panel is not visible
        return None

    if not addon_props.panelvis_object_attributes and not force_run:
        # Skip update if rollout is not visible
        return None

    attrs_to_keep_str: str = addon_prefs.object_attributes_to_keep  # comma-separated list
    attrs_to_keep = set(attrs_to_keep_str.replace(" ", "").split(","))

    if get_selected_objects() or force_run:
        current_selection_names = sorted([obj.name for obj in iter_scene_objects(selected=True)])
        current_selection_str = ",".join(current_selection_names)

        # Store the current selection state before clearing the list
        selection_state = _object_attributes_store_states()

        try:
            addon_props.object_attributes_list.clear()
        except Exception as e:
            log.error(f"{e}")
            return None

        # Add unique custom properties to the set
        unique_attributes = set()
        if current_selection_names:
            for obj in iter_scene_objects(selected=True):
                if not hasattr(obj.data, "attributes"):
                    continue

                # Object Attributes
                for attrib_name, attrib_data in obj.data.attributes.items():
                    log.debug(f"(ObjAttrib) {obj.name} - {attrib_name=}")

                    # position attribute is required and can't be removed
                    if attrib_name == "position":
                        continue

                    if not attrib_name.startswith(".") and attrib_name not in attrs_to_keep:
                        unique_attributes.add(attrib_name)

            # Populate the UIList
            object_attributes_list_add_props(unique_attributes, selection_state)

        # Update the last object selection
        addon_props.last_object_selection = current_selection_str

        # Force UI update
        for area in bpy.context.screen.areas:
            if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
                area.tag_redraw()

    else:
        # Store the states even if nothing selected
        selection_state = _object_attributes_store_states()

        # Clear the property list if no objects are selected
        try:
            addon_props.object_attributes_list.clear()
            log.debug(f"Cleared UIList object_attributes_list")
        except Exception as e:
            log.error(f"Error clearing custom property list when no selected objects: {e}")
            context_error_debug(error=e)
        try:
            addon_props.last_object_selection = ""
            log.debug(f"Cleared property last_object_selection")
        except Exception as e:
            log.error(f"Error setting last object selection when no selected objects: {e}")
            context_error_debug(error=e)

        # Force UI update
        if bpy.context.screen:
            if hasattr(bpy.context.screen, "areas"):
                for area in bpy.context.screen.areas:
                    if area.type in {"PROPERTIES", "OUTLINER", "VIEW_3D"}:
                        area.tag_redraw()

    return None


def create_panel_variant(panel_class, space_type: str = None, region_type: str = None, category: str = None):
    if space_type:
        identifier = space_type.replace(" ", "_").lower()
    elif region_type:
        identifier = region_type.replace(" ", "_").lower()
    elif category:
        identifier = category.replace(" ", "_").lower()
    else:
        identifier = "bare"

    # Create new class
    class_name = f"{panel_class.__name__}_{identifier}"

    # Get original bl_idname without modifications
    original_idname = getattr(panel_class, "_original_bl_idname", panel_class.bl_idname)

    # Create class attributes
    attrs = {
        "bl_idname": f"{original_idname}_{identifier}",
        "bl_label": panel_class.bl_label,
        "bl_space_type": space_type or panel_class.bl_space_type,
        "bl_region_type": region_type or panel_class.bl_region_type,
        "bl_category": category or getattr(panel_class, "bl_category", "Misc"),
        "_original_bl_idname": original_idname,  # Store original for reference
        "draw": panel_class.draw,  # Copy draw method
    }

    # Copy any other methods or attributes
    for attr_name in dir(panel_class):
        if not attr_name.startswith("bl_") and not attr_name.startswith("_"):
            attr = getattr(panel_class, attr_name)
            if callable(attr) and attr_name not in {"draw"}:
                attrs[attr_name] = attr

    new_class = type(class_name, (bpy.types.Panel,), attrs)

    return new_class


def context_error_debug(error: str = None, extra_prints: list = []):
    """Print debug information about the current context and error"""
    import inspect

    log.debug(f"+" * 32)
    if error:
        log.debug(f"Associated Error (below):")
        log.debug(f"{error}")

    if bpy.app.background:
        log.debug(f"Running in background mode - ID writing may be restricted.")

    if bpy.ops.wm.save_as_mainfile.poll() == False:
        log.debug(f"Restricted context - file saving not allowed.")

    log.debug(f" bpy.context:", bpy.context)
    if bpy.context:
        log.debug(f"bpy.context.scene:", bpy.context.scene)
        log.debug(f"bpy.context.area:", bpy.context.area)
        log.debug(f"bpy.context.mode:", bpy.context.mode)
        log.debug(f"bpy.context.window:", bpy.context.window)
        log.debug(f"bpy.context.space_data:", bpy.context.space_data)
        log.debug(f"bpy.context.region:", bpy.context.region)
        log.debug(f"bpy.context.region_data:", bpy.context.region_data)
    log.debug(f"Window Manager debug mode:", bpy.app.debug_wm)

    log.debug(f"Current Handlers:")
    for handler in bpy.app.handlers.depsgraph_update_post:
        log.debug(f"   - {handler.__name__}")

    log.debug(f"Call Stack:")
    for frame in inspect.stack():
        log.debug(f"  File: {frame.filename}, Line: {frame.lineno}, Function: {frame.function}")

    if extra_prints:
        log.debug()
        log.debug(f"Extra Prints")
        for extra_print in extra_prints:
            log.debug(f"Extra: {extra_print}")

    log.debug(f"+" * 32)
