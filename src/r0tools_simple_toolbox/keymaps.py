import bpy
import rna_keymap_ui

from . import utils as u

KEYMAP_CONFIGS = {
    "r0tools.toggle_wire_display_mode": {
        "default_key": "FOUR",  # Default key if no user override.
        "keymap_context_name": "Object Mode",  # The keymap (context) name.
        "space_type": "EMPTY",  # Typically "EMPTY" for mode-specific maps.
        "value": "PRESS",  # Event value.
        "addon_pref_prop": "keymap_toggle_wire",  # Property name in Addon Preferences.
    },
    "r0tools.object_sets_modal": {
        "default_key": "ONE",  # Default key if no user override.
        "keymap_context_name": "Object Mode",  # The keymap (context) name.
        "space_type": "EMPTY",  # Typically "EMPTY" for mode-specific maps.
        "value": "PRESS",  # Event value.
        "addon_pref_prop": "keymap_object_sets_modal",  # Property name in Addon Preferences.
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
        context_space = cfg.get("keymap_context_name", "")

        if not context_space:
            continue

        # Setdefault to accumulate multiple ops under the same context.
        # Avoid manual check re-implementation
        context_space_dict.setdefault(context_space, {})[op_id] = cfg

    return context_space_dict


# Store the result of collecting keymaps by context space.
# Keep as constant, therefore removing the necessity to always call the method
# to collect existing keymaps. Needs only to import the const reference.
KEYMAPS_CONTEXT_SPACE_CONFIGS = collect_keymaps_by_context_space()


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

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user

    index_by_context_space_keymaps = KEYMAPS_CONTEXT_SPACE_CONFIGS

    keymaps_box = layout.box()
    keymaps_box.label(text="Keymaps:")

    object_mode_box = layout.box()
    for context_region, keymaps in index_by_context_space_keymaps.items():
        row = object_mode_box.row()
        row.label(text=f"{context_region}:")
        for op_id, cfg in keymaps.items():
            km = kc.keymaps[context_region]
            kmi = get_hotkey_entry_item(km, op_id, "none", "none")
            if kmi:
                row = object_mode_box.row()
                row.context_pointer_set("keymap", km)
                rna_keymap_ui.draw_kmi([], kc, km, kmi, row, 0)
            else:
                row = object_mode_box.row()
                row.label(text=f"No hotkey found for '{op_id}' or is being by another addon.")


addon_keymaps = []


def register_keymaps():
    print(f"[KEYMAPS] Register Keymaps")
    addon_prefs = u.get_addon_prefs()
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:
        # Iterate over each operator keymap configuration
        for op_id, cfg in KEYMAP_CONFIGS.items():
            # Get (or create) the desired keymap by name.
            km = kc.keymaps.get(cfg["keymap_context_name"])
            key = cfg.get("default_key", "")
            if km is None:
                km = kc.keymaps.new(
                    name=cfg["keymap_context_name"],
                    space_type=cfg["space_type"],
                    type=key,
                )

            # Prevent duplicates
            if not any(kmi.idname == op_id for kmi in km.keymap_items):
                # Get the user-defined key from the addon preferences otherwise default.
                key = getattr(addon_prefs, cfg["addon_pref_prop"], cfg["default_key"])
                kmi = km.keymap_items.new(op_id, type=key, value=cfg["value"])
                addon_keymaps.append((km, kmi))


def unregister_keymaps():
    print(f"[KEYMAPS] Unregister Keymaps")

    for km, kmi in addon_keymaps:
        print(f"[KEYMAPS] Remove {kmi.idname}")
        km.keymap_items.remove(kmi)

    addon_keymaps.clear()


def register():
    register_keymaps()


def unregister():
    unregister_keymaps()
