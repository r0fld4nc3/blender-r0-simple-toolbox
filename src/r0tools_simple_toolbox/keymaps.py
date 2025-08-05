import bpy
import rna_keymap_ui
from bpy.props import StringProperty

from . import utils as u
from .defines import DEBUG
from .object_sets.operators import SimpleToolbox_OT_ObjectSetsModal
from .operators import (
    SimpleToolbox_OT_ShowCustomOrientationsPie,
    SimpleToolbox_OT_ToggleWireDisplay,
)

_mod = "KEYMAPS"

KEYMAP_CONFIGS = {
    SimpleToolbox_OT_ToggleWireDisplay.bl_idname: {
        "default_key": "FOUR",
        "keymap_name": "3D View",
        "space_type": "VIEW_3D",  # Change to "EMPTY" if using "Object Mode" keymap_name ; Change to "VIEW_3D" if using "3d View" keymap_name
        "region_type": "WINDOW",
        "value": "PRESS",
        "addon_pref_prop": "keymap_toggle_wire_display_mode",
    },
    SimpleToolbox_OT_ObjectSetsModal.bl_idname: {
        "default_key": "ONE",
        "keymap_name": "3D View",
        "space_type": "VIEW_3D",  # Change to "EMPTY" if using "Object Mode" keymap_name ; Change to "VIEW_3D" if using "3d View" keymap_name
        "region_type": "WINDOW",
        "value": "PRESS",
        "addon_pref_prop": "keymap_object_sets_modal",
    },
    SimpleToolbox_OT_ShowCustomOrientationsPie.bl_idname: {
        "default_key": "NONE",
        "keymap_name": "3D View",
        "space_type": "VIEW_3D",  # Change to "EMPTY" if using "Object Mode" keymap_name ; Change to "VIEW_3D" if using "3d View" keymap_name
        "region_type": "WINDOW",
        "value": "PRESS",
        "addon_pref_prop": "keymap_show_custom_orientations_pie",
        "show_in_assign": False,
    },
}


def collect_keymaps_by_context_space() -> dict:
    """
    Collect available keymaps by their Region Context Name and return a dictionary
    where base keys are the Region Context Name and the values are another dictionary
    mapping the Operation ID to its configuration.
    """
    context_space_dict = {}

    for op_id, cfg in KEYMAP_CONFIGS.items():
        keymap_name = cfg.get("keymap_name", "")
        if keymap_name:
            context_space_dict.setdefault(keymap_name, {})[op_id] = cfg

    return context_space_dict


KEYMAPS_CONTEXT_SPACE_CONFIGS = collect_keymaps_by_context_space()


def get_hotkey_entry_item(km, kmi_name):
    """
    Get a keymap item by operator name.
    """
    for kmi in km.keymap_items:
        if kmi.idname == kmi_name:
            return kmi
    return None


def draw_keymap_settings(layout, prefs):
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user

    keymaps_box = layout.box()
    keymaps_box.label(text="Keymaps:")

    for keymap_name, keymaps in KEYMAPS_CONTEXT_SPACE_CONFIGS.items():
        context_box = keymaps_box.box()
        context_box.label(text=f"{keymap_name}:")

        visible_keymaps = {op_id: cfg for op_id, cfg in keymaps.items() if cfg.get("show_in_assign", True)}

        if not visible_keymaps:
            continue

        # Access the existing keymap
        km = None
        for keymap in kc.keymaps:
            if keymap.name == keymap_name:
                km = keymap
                break

        if km:
            for op_id, cfg in visible_keymaps.items():
                kmi = get_hotkey_entry_item(km, op_id)
                if kmi:
                    row = context_box.row()
                    row.context_pointer_set("keymap", km)

                    # Handling for unassigned keys
                    if kmi.type == "NONE":
                        split = row.split(factor=0.6)
                        split.label(text=f"{op_id} (No Key Assigned)")

                        assign_op = split.operator("r0tools.assign_keymap", text="Assign Key")
                        assign_op.op_id = op_id
                    else:
                        # Draw the standard keymap item
                        rna_keymap_ui.draw_kmi([], kc, km, kmi, row, 0)

                    # Update addon preferences if key changed
                    if hasattr(prefs, cfg["addon_pref_prop"]):
                        stored_key = getattr(prefs, cfg["addon_pref_prop"])
                        current_key = kmi.type if kmi.type != "NONE" else "NONE"
                        if stored_key != current_key:
                            setattr(prefs, cfg["addon_pref_prop"], current_key)
                else:
                    row = context_box.row()
                    row.label(text=f"No hotkey found for '{op_id}'")
                    row.operator("r0tools.restore_keymap", text="Restore").op_id = op_id
        else:
            context_box.label(text=f"Keymap '{keymap_name}' not found", icon="ERROR")


class SimpleToolbox_OT_Assign_Keymap(bpy.types.Operator):
    """Assign a key to an unassigned keymap item."""

    bl_idname = "r0tools.assign_keymap"
    bl_label = "Assign Key to Keymap"
    bl_description = "Assign a key to this unassigned keymap item"

    op_id: StringProperty()  # type: ignore

    def execute(self, context):
        self.report({"INFO"}, f"Use the keymap editor below to assign a key to {self.op_id}")
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        layout.label(text="To assign a key to this operator:")
        layout.label(text="1. Find the entry in the keymap list below")
        layout.label(text="2. Click in the key field")
        layout.label(text="3. Press your desired key combination")
        layout.separator()
        layout.label(text=f"Operator: {self.op_id}")


class SimpleToolbox_OT_Restore_Keymap(bpy.types.Operator):
    """Restore a missing keymap item"""

    bl_idname = "r0tools.restore_keymap"
    bl_label = "Restore Keymap"

    op_id: StringProperty()  # type: ignore

    def execute(self, context):
        cfg = KEYMAP_CONFIGS.get(self.op_id)
        if not cfg:
            return {"CANCELLED"}

        addon_prefs = u.get_addon_prefs()
        wm = context.window_manager
        kc = wm.keyconfigs.addon  # Use addon keyconfig to restore

        # Get or create keymap
        km = None
        for keymap in kc.keymaps:
            if (
                keymap.name == cfg["keymap_name"]
                and keymap.space_type == cfg["space_type"]
                and keymap.region_type == cfg["region_type"]
            ):
                km = keymap
                break

        if not km:
            km = kc.keymaps.new(name=cfg["keymap_name"], space_type=cfg["space_type"], region_type=cfg["region_type"])

        if km:
            # Get key from preferences or use default
            key = getattr(addon_prefs, cfg["addon_pref_prop"], cfg["default_key"])
            kmi = km.keymap_items.new(self.op_id, type=key, value=cfg["value"])
            addon_keymaps.append((km, kmi))

            self.report({"INFO"}, f"Restored keymap for {self.op_id}")
        else:
            self.report({"ERROR"}, f"Could not find keymap '{cfg['keymap_name']}'")

        return {"FINISHED"}


addon_keymaps = []


def register_keymaps():
    """Register keymaps with support for optional key assignments."""
    if DEBUG:
        print(f"[INFO] [{_mod}] Register Keymaps")

    addon_prefs = u.get_addon_prefs()
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if not kc:
        print(f"[WARNING] [{_mod}] No addon keyconfig available")
        return

    for op_id, cfg in KEYMAP_CONFIGS.items():
        keymap_name = cfg["keymap_name"]
        space_type = cfg["space_type"]
        region_type = cfg["region_type"]

        # Find existing keymap or create new one
        km = None
        for keymap in kc.keymaps:
            if keymap.name == keymap_name and keymap.space_type == space_type and keymap.region_type == region_type:
                km = keymap
                break

        if not km:
            km = kc.keymaps.new(name=keymap_name, space_type=space_type, region_type=region_type)
            if DEBUG:
                print(f"[INFO] [{_mod}] Created new keymap '{keymap_name}'")

        # Check if keymap item already exists
        existing_kmi = get_hotkey_entry_item(km, op_id)

        if not existing_kmi:
            # Determine key to use
            key = cfg["default_key"]

            # Check if there's a stored preference
            if hasattr(addon_prefs, cfg["addon_pref_prop"]):
                stored_key = getattr(addon_prefs, cfg["addon_pref_prop"])
                if stored_key and stored_key != "NONE":
                    key = stored_key

            # Create keymap item even with "NONE" key
            try:
                kmi = km.keymap_items.new(op_id, type=key, value=cfg["value"])
                addon_keymaps.append((km, kmi))

                if DEBUG:
                    status = "unassigned" if key == "NONE" else f"with key {key}"
                    print(f"[INFO] [{_mod}] Registered {op_id} {status}")

            except Exception as e:
                print(f"[ERROR] [{_mod}] Failed to register {op_id}: {e}")
        else:
            # Update preference to match existing keymap
            if hasattr(addon_prefs, cfg["addon_pref_prop"]):
                current_key = existing_kmi.type if existing_kmi.type != "NONE" else "NONE"
                setattr(addon_prefs, cfg["addon_pref_prop"], current_key)

            addon_keymaps.append((km, existing_kmi))
            if DEBUG:
                print(f"[INFO] [{_mod}] Found existing keymap for {op_id}")


def unregister_keymaps():
    if DEBUG:
        print(f"[INFO] [{_mod}] Unregister Keymaps")

    # Save current keybinds to preferences before removing
    addon_prefs = u.get_addon_prefs()

    for km, kmi in addon_keymaps:
        cfg = KEYMAP_CONFIGS.get(kmi.idname)
        if cfg and hasattr(addon_prefs, cfg["addon_pref_prop"]):
            setattr(addon_prefs, cfg["addon_pref_prop"], kmi.type)

        try:
            if DEBUG:
                print(f"[INFO] [{_mod}] Remove {kmi.idname}")
            km.keymap_items.remove(kmi)
        except Exception as e:
            print(f"[WARNING] [{_mod}] Could not remove {kmi.idname}: {e}")

    addon_keymaps.clear()


classes = [
    SimpleToolbox_OT_Assign_Keymap,
    SimpleToolbox_OT_Restore_Keymap,
]


def register():
    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    register_keymaps()


def unregister():
    unregister_keymaps()

    for cls in classes:
        if DEBUG:
            print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
