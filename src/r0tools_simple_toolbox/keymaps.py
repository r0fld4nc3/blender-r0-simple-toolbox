import bpy
from . import utils as u
import rna_keymap_ui

KEYMAP_CONFIGS = {
    "object.toggle_wire_display_mode": {
        "default_key": "FOUR",                    # Default key if no user override.
        "keymap_context_name": "Object Mode",     # The keymap (context) name.
        "space_type": "EMPTY",                    # Typically "EMPTY" for mode-specific maps.
        "value": "PRESS",                         # Event value.
        "addon_pref_prop": "keymap_toggle_wire",  # Property name in Addon Preferences.
    },
    "r0tools.object_sets_modal": {
        "default_key": "ONE",                    # Default key if no user override.
        "keymap_context_name": "Object Mode",     # The keymap (context) name.
        "space_type": "EMPTY",                    # Typically "EMPTY" for mode-specific maps.
        "value": "PRESS",                         # Event value.
        "addon_pref_prop": "keymap_object_sets_modal",  # Property name in Addon Preferences.
    },
}


def get_hotkey_entry_item(km, kmi_name, kmi_value, properties):
    # Thank you HardOps <3
    for i, km_item in enumerate(km.keymap_items):
        if km.keymap_items.keys()[i] == kmi_name:
            if properties == "name":
                if km.keymap_items[i].properties.name == kmi_value:
                    return km_item
            elif properties == "tab":
                if km.keymap_items[i].properties.tab == kmi_value:
                    return km_item
            elif properties == "none":
                return km_item
    return None


def draw_keymap_settings(layout, prefs):
    """
    Draws the keymap section in the addon preferences UI

    :param layout: The layout from the preferences panel.
    :param prefs: The AddonPreferences instance containing the keymap properties.
    """

    keymaps_box = layout.box()
    keymaps_box.label(text="Keymaps:")

    object_mode_box = layout.box()
    row = object_mode_box.row()
    row.label(text="Object Mode:")
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    
    # Toggle Wire Display
    km = kc.keymaps["Object Mode"]
    kmi = get_hotkey_entry_item(km, "object.toggle_wire_display_mode", "none", "none")
    row = object_mode_box.row()
    if kmi:
        row.context_pointer_set("keymap", km)
        rna_keymap_ui.draw_kmi([], kc, km, kmi, row, 0)
    else:
        row.label(text="No hotkey entry found")

    # Object Sets Modal
    km = kc.keymaps["Object Mode"]
    kmi = get_hotkey_entry_item(km, "r0tools.object_sets_modal", "none", "none")
    row = object_mode_box.row()
    if kmi:
        row.context_pointer_set("keymap", km)
        rna_keymap_ui.draw_kmi([], kc, km, kmi, row, 0)
    else:
        row.label(text="No hotkey entry found")

addon_keymaps = list()

def register_keymaps():
    print(f"[KEYMAPS] Registering Keymaps")
    addon_prefs = u.get_addon_prefs()
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:
        # Iterate over each operator keymap configuration
        for op_id, cfg in KEYMAP_CONFIGS.items():
            # Get (or create) the desired keymap by name.
            km = kc.keymaps.get(cfg["keymap_context_name"])
            if km is None:
                km = kc.keymaps.new(name=cfg["keymap_context_name"], space_type=cfg["space_type"], type=key)
                print(f"[KEYMAPS] Added Keymap: {op_id}")

            # Prevent duplicates
            if not any(kmi.idname == op_id for kmi in km.keymap_items):
                print(f"[KEYMAPS] Other Section: {op_id}")
                # Get the user-defined key from the addon preferences otherwise default.
                key = getattr(addon_prefs, cfg["addon_pref_prop"], cfg["default_key"])
                kmi = km.keymap_items.new(op_id, type=key, value=cfg["value"])
                addon_keymaps.append((km, kmi))


def unregister_keymaps():
    print(f"[KEYMAPS] Unregistering Keymaps")

    for km, kmi in addon_keymaps:
        print(f"[KEYMAPS] Remove {kmi.idname}")
        km.keymap_items.remove(kmi)
    
    addon_keymaps.clear()


def register():
    register_keymaps()


def unregister():
    unregister_keymaps()
