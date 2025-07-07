import bpy
import rna_keymap_ui
from bpy.props import StringProperty

from . import utils as u

_mod = "KEYMAPS"

KEYMAP_CONFIGS = {
    "r0tools.toggle_wire_display_mode": {
        "default_key": "FOUR",
        "keymap_name": "Object Mode",
        "space_type": "EMPTY",
        "region_type": "WINDOW",
        "value": "PRESS",
        "addon_pref_prop": "keymap_toggle_wire",
    },
    "r0tools.object_sets_modal": {
        "default_key": "ONE",
        "keymap_name": "Object Mode",
        "space_type": "EMPTY",
        "region_type": "WINDOW",
        "value": "PRESS",
        "addon_pref_prop": "keymap_object_sets_modal",
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

        # Access the existing keymap. Don't create a new one
        km = None
        for keymap in kc.keymaps:
            if keymap.name == keymap_name:
                km = keymap
                break

        if km:
            for op_id, cfg in keymaps.items():
                kmi = get_hotkey_entry_item(km, op_id)
                if kmi:
                    row = context_box.row()
                    row.context_pointer_set("keymap", km)

                    # Draw the keymap item
                    rna_keymap_ui.draw_kmi([], kc, km, kmi, row, 0)

                    # Update addon preferences if key changed
                    if hasattr(prefs, cfg["addon_pref_prop"]):
                        stored_key = getattr(prefs, cfg["addon_pref_prop"])
                        if stored_key != kmi.type:
                            setattr(prefs, cfg["addon_pref_prop"], kmi.type)
                else:
                    row = context_box.row()
                    row.label(text=f"No hotkey found for '{op_id}'")

                    # Add button to restore the keymap
                    row.operator("r0tools.restore_keymap", text="Restore").op_id = op_id
        else:
            context_box.label(text=f"Keymap '{keymap_name}' not found", icon="ERROR")


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

        # Find existing keymap
        km = None
        for keymap in kc.keymaps:
            if keymap.name == cfg["keymap_name"]:
                km = keymap
                break

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
    print(f"[INFO] [{_mod}] Register Keymaps")
    addon_prefs = u.get_addon_prefs()
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if not kc:
        print(f"[WARNING] [{_mod}] No addon keyconfig available")
        return

    for op_id, cfg in KEYMAP_CONFIGS.items():
        keymap_name = cfg["keymap_name"]

        # Find the existing keymap. Don't create a new one!
        km = None
        for keymap in kc.keymaps:
            if keymap.name == keymap_name:
                km = keymap
                break

        if not km:
            print(f"[WARNING] [{_mod}] Keymap '{keymap_name}' not found")
            continue

        # Check if keymap item already exists
        existing_kmi = get_hotkey_entry_item(km, op_id)

        if not existing_kmi:
            # Get the key from addon preferences or use default
            key = cfg["default_key"]  # Default fallback
            if hasattr(addon_prefs, cfg["addon_pref_prop"]):
                stored_key = getattr(addon_prefs, cfg["addon_pref_prop"])
                if stored_key:  # Only use if not empty
                    key = stored_key

            # Create the keymap item
            try:
                kmi = km.keymap_items.new(op_id, type=key, value=cfg["value"])
                addon_keymaps.append((km, kmi))
                print(f"[INFO] [{_mod}] Registered {op_id} with key {key}")
            except Exception as e:
                print(f"[ERROR] [{_mod}] Failed to register {op_id}: {e}")
        else:
            # Update the preference to match existing keymap
            if hasattr(addon_prefs, cfg["addon_pref_prop"]):
                setattr(addon_prefs, cfg["addon_pref_prop"], existing_kmi.type)
            addon_keymaps.append((km, existing_kmi))
            print(f"[INFO] [{_mod}] Found existing keymap for {op_id}")


def unregister_keymaps():
    print(f"[INFO] [{_mod}] Unregister Keymaps")

    # Save current keybinds to preferences before removing
    addon_prefs = u.get_addon_prefs()

    for km, kmi in addon_keymaps:
        cfg = KEYMAP_CONFIGS.get(kmi.idname)
        if cfg and hasattr(addon_prefs, cfg["addon_pref_prop"]):
            setattr(addon_prefs, cfg["addon_pref_prop"], kmi.type)

        try:
            print(f"[INFO] [{_mod}] Remove {kmi.idname}")
            km.keymap_items.remove(kmi)
        except Exception as e:
            print(f"[WARNING] [{_mod}] Could not remove {kmi.idname}: {e}")

    addon_keymaps.clear()


classes = [
    SimpleToolbox_OT_Restore_Keymap,
]


def register():
    for cls in classes:
        print(f"[INFO] [{_mod}] Register {cls.__name__}")
        bpy.utils.register_class(cls)

    register_keymaps()


def unregister():
    unregister_keymaps()

    for cls in classes:
        print(f"[INFO] [{_mod}] Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
