import bpy
from bpy.props import (
    BoolProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    StringProperty,
)

from .. import utils as u

_mod = "DATA_OPS.DATA_OPERATORS"


class SimpleToolbox_OT_ClearCustomSplitNormalsData(bpy.types.Operator):
    bl_label = "Clear Split Normals"
    bl_idname = "r0tools.clear_custom_split_normals_data"
    bl_description = "Clears the Custom Split Normals assignments for selected objects and sets AutoSmooth to 180.\nUseful to quickly clear baked normals/shading assignments of multiple meshes at once"
    bl_options = {"REGISTER", "UNDO"}

    accepted_contexts = [u.OBJECT_MODES.OBJECT, u.OBJECT_MODES.EDIT_MESH]

    @classmethod
    def poll(cls, context):
        return context.mode in cls.accepted_contexts and u.get_selected_objects(context)

    def op_clear_custom_split_normals_data(self, objects):
        """
        Clears the Custom Split Normals assignments for selected objects and sets AutoSmooth to 180.

        Useful to quickly clear baked normals/shading assignments of multiple meshes at once.
        """

        for obj in objects:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
            bpy.ops.object.shade_smooth()
            # bpy.ops.object.shade_smooth() # Not needed. Will give an error if Weighted Normals modifier is present.
            # bpy.context.object.data.use_auto_smooth = True
            # bpy.context.object.data.auto_smooth_angle = 3.14159

    def execute(self, context):
        if u.is_debug():
            print("\n------------- Clear Custom Split Normals Data -------------")
        orig_context = context.mode
        orig_active = bpy.context.view_layer.objects.active

        if context.mode == u.OBJECT_MODES.EDIT_MESH:
            u.set_mode_object()

        objects = [obj for obj in u.iter_scene_objects(selected=True, types=[u.OBJECT_TYPES.MESH])]
        self.op_clear_custom_split_normals_data(objects)
        bpy.context.view_layer.objects.active = orig_active

        if orig_context != u.OBJECT_MODES.OBJECT and orig_context == u.OBJECT_MODES.EDIT_MESH:
            u.set_mode_edit()

        msg = f"Finished clearing Custom Split Data across {len(objects)} objects"
        # u.show_notification(msg)
        self.report({"INFO"}, msg)
        return {"FINISHED"}


class SimpleToolbox_OT_ClearCustomProperties(bpy.types.Operator):
    bl_label = "Delete"
    bl_idname = "r0tools.delete_custom_properties"
    bl_description = "Delete Custom Properties from Object(s)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return u.get_selected_objects(context)

    def execute(self, context):
        addon_props = u.get_addon_props()

        if u.is_debug():
            print("\n------------- Clear Custom Properties -------------")
        object_data_property_deletions = set()
        mesh_data_property_deletions = set()
        total_deletions = 0
        total_objects = 0

        # Find selected properties to remove
        props_to_remove = [item for item in addon_props.custom_property_list if item.selected]

        for obj in context.selected_objects:
            # Remove selected properties
            for custom_prop in props_to_remove:
                prop_name = custom_prop.name
                prop_type = custom_prop.type

                # Object Data
                if prop_type == u.CUSTOM_PROPERTIES_TYPES.OBJECT_DATA:
                    if prop_name in reversed(obj.keys()):
                        if u.is_debug():
                            print(f"[DEBUG] [{_mod}] Deleting Object Data Property '{prop_name}' of object {obj.name}")
                        del obj[prop_name]
                        object_data_property_deletions.add(prop_name)
                        total_objects += 1
                # Mesh Data
                elif prop_type == u.CUSTOM_PROPERTIES_TYPES.MESH_DATA:
                    if prop_name in reversed(obj.data.keys()):
                        if u.is_debug():
                            print(f"[DEBUG] [{_mod}] Deleting Mesh Data Property '{prop_name}' of object {obj.name}")
                        del obj.data[prop_name]
                        mesh_data_property_deletions.add(prop_name)
                        total_objects += 1

        total_deletions = len(object_data_property_deletions) + len(mesh_data_property_deletions)

        u.property_list_update(force_run=True)

        # u.show_notification(f"Deleted {total_deletions} propertie(s) across {total_objects} object(s)")
        self.report(
            {"INFO"},
            f"Deleted {total_deletions} propertie(s) across {total_objects} object(s)",
        )
        return {"FINISHED"}


class SimpleToolbox_OT_ClearObjectAttributes(bpy.types.Operator):
    bl_label = "Delete"
    bl_idname = "r0tools.delete_object_attributes"
    bl_description = "Delete Attributes from Object(s)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return u.get_selected_objects(context)

    def execute(self, context):
        addon_prefs = u.get_addon_prefs()
        addon_props = u.get_addon_props()

        attrs_to_keep_str: str = addon_prefs.object_attributes_to_keep  # comma-separated list
        attrs_to_keep = set(attrs_to_keep_str.replace(" ", "").split(","))

        if u.is_debug():
            print("\n------------- Clear Object Attributes -------------")
        attributes_property_deletions = set()
        total_deletions = 0
        total_objects = 0

        errors = []  # Build list and do a single final batch print

        # Find selected properties to remove
        attribs_to_remove = [
            item for item in addon_props.object_attributes_list if item.selected and item not in attrs_to_keep
        ]

        print(attribs_to_remove)

        for obj in context.selected_objects:
            data = obj.data

            if not hasattr(data, "attributes"):
                continue

            # Remove selected properties
            for attribute_prop in attribs_to_remove:
                attrib_name = attribute_prop.name

                # Object Data
                if attrib_name in reversed(obj.data.attributes.keys()):
                    if u.is_debug():
                        print(f"[DEBUG] [{_mod}] Deleting Attribute '{attrib_name}' of object {obj.name}")

                    try:
                        data.attributes.remove(data.attributes[attrib_name])
                    except Exception as e:
                        errors.append(
                            f"[ERROR] [{_mod}] Unable to remove attribute '{attrib_name}' from '{obj.name}': {e}"
                        )
                        continue
                    attributes_property_deletions.add(attrib_name)
                    total_deletions += 1

            total_objects += 1

        u.object_attributes_list_update(force_run=True)

        if errors:
            print("".join(errors))

        # u.show_notification(f"Deleted {total_deletions} propertie(s) across {total_objects} object(s)")
        self.report(
            {"INFO"},
            f"Deleted {total_deletions} attributes from {total_objects} object(s)",
        )
        return {"FINISHED"}


class SimpleToolbox_OT_ObjectAttributesRestoreDefaults(bpy.types.Operator):
    bl_label = "Reset"
    bl_idname = "r0tools.object_attributes_restore_defaults"
    bl_description = "Restores default list of attributes to keep"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        addon_prefs = u.get_addon_prefs()

        prop_rna = addon_prefs.bl_rna.properties["object_attributes_to_keep"]
        default = prop_rna.default

        addon_prefs.object_attributes_to_keep = default

        self.report({"INFO"}, f"Restored default attributes to keep: {default}")
        return {"FINISHED"}


class SimpleToolbox_OT_ClearMeshAttributes(bpy.types.Operator):
    bl_label = "Clear Attributes"
    bl_idname = "r0tools.clear_mesh_attributes"
    bl_description = "Clears unneeded mesh(es) attributes created by various addons.\nPreserves some integral and needed attributes such as material_index that is required for multi-material assignments.\nSometimes certain addons or operations will populate this list with attributes you wish to remove at a later date, be it for parsing or exporting"
    bl_options = {"REGISTER", "UNDO"}

    def op_clear_mesh_attributes(self):
        """
        Clears unneeded mesh(es) attributes created by various addons. Preserves some integral and needed attributes such as material_index that is required for multi-material assignments.

        Sometimes certain addons or operations will populate this list with attributes you wish to remove at a later date, be it for parsing or exporting.
        """

        u.log(f"[INFO] [{_mod}] [CLEAR MESH ATTRIBUTES]")

        initial_obj = bpy.context.active_object

        exclude_filter = ("colorSet", "map", "material_index")  # Starts with these tags
        attrs_check = (
            bpy.types.IntAttribute,
            bpy.types.FloatAttribute,
            bpy.types.FloatColorAttribute,
            bpy.types.StringAttribute,
            bpy.types.ByteColorAttribute,
            bpy.types.FloatVectorAttribute,
            bpy.types.FloatVectorAttributeValue,
        )

        for obj in u.get_selected_objects():
            if obj.type == u.OBJECT_TYPES.MESH:
                bpy.context.view_layer.objects.active = obj
                mesh = bpy.context.object.data
                if u.is_debug():
                    print(f"[DEBUG] [{_mod}] Object: {mesh.name}")
                try:
                    for at in reversed(mesh.attributes.items()):
                        # Check if not T4 Attribute
                        if not isinstance(at[1], attrs_check):
                            continue

                        at_name = at[0]
                        if str(at_name).startswith(exclude_filter):
                            if u.is_debug():
                                print(f"[DEBUG] [{_mod}] {' '*2}Keeping Attribute: {at_name}")
                        else:
                            if u.is_debug():
                                print(f"[DEBUG] [{_mod}] {' '*2}Removing Attribute: {at[0]}")
                            mesh.color_attributes.remove(at[1])
                except Exception as e:
                    print(f"[ERROR] [{_mod}] Error Clearing Mesh Attributes")
                    u.context_error_debug(error=e)

        bpy.context.view_layer.objects.active = initial_obj

    def execute(self, context):
        if u.is_debug():
            print("\n------------- Clear Mesh Attributes -------------")
        self.op_clear_mesh_attributes()
        return {"FINISHED"}

    # fmt: off


classes = [
    SimpleToolbox_OT_ClearCustomSplitNormalsData,
    SimpleToolbox_OT_ClearCustomProperties,
    SimpleToolbox_OT_ClearObjectAttributes,
    SimpleToolbox_OT_ObjectAttributesRestoreDefaults,
    SimpleToolbox_OT_ClearMeshAttributes,
]
# fmt: on


def register():
    for cls in classes:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        if u.is_debug():
            print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
