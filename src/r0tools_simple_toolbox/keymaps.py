import logging

import bpy
import rna_keymap_ui
from bpy.props import StringProperty

from .object_sets.operators import SimpleToolbox_OT_ObjectSetsModal
from .operators import (
    SimpleToolbox_OT_ShowCustomOrientationsPie,
    SimpleToolbox_OT_ToggleWireDisplay,
)
from .vertex_groups.operators import SimpleToolbox_OT_VertexGroupsModal

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keymap configuration
# ---------------------------------------------------------------------------
# "default_key": "NONE" = operator is unbound by default.
# "show_in_prefs": False = hide from the addon preferences UI.

KEYMAP_CONFIGS: dict[str, dict] = {
    SimpleToolbox_OT_ToggleWireDisplay.bl_idname: {
        "label": "Toggle Wire Display",
        "default_key": "NONE",
        "keymap_name": "3D View",
        "space_type": "VIEW_3D",
        "value": "PRESS",
    },
    SimpleToolbox_OT_ObjectSetsModal.bl_idname: {
        "label": "Object Sets Modal",
        "default_key": "NONE",
        "keymap_name": "3D View",
        "space_type": "VIEW_3D",
        "value": "PRESS",
    },
    SimpleToolbox_OT_VertexGroupsModal.bl_idname: {
        "label": "Vertex Groups Modal",
        "default_key": "NONE",
        "keymap_name": "3D View",
        "space_type": "VIEW_3D",
        "value": "PRESS",
    },
    SimpleToolbox_OT_ShowCustomOrientationsPie.bl_idname: {
        "label": "Custom Orientations Pie",
        "default_key": "NONE",
        "keymap_name": "3D View",
        "space_type": "VIEW_3D",
        "value": "PRESS",
        "show_in_prefs": False,
    },
}

# Tracks (km, kmi) pairs created by this addon for clean unregistration.
_addon_keymaps: list[tuple[str, bpy.types.KeyMap, bpy.types.KeyMapItem]] = []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _matching_kmis(
    km: bpy.types.KeyMap | None,
    op_id: str,
    properties: list[tuple[str, object]] | None = None,
) -> list[bpy.types.KeyMapItem]:
    if km is None:
        return []

    matches: list[bpy.types.KeyMapItem] = []
    for kmi in km.keymap_items:
        if kmi.idname != op_id:
            continue

        if properties:
            if not all(getattr(kmi.properties, name, None) == value for name, value in properties):
                continue

        matches.append(kmi)

    return matches


def _find_kmi(
    km: bpy.types.KeyMap | None,
    op_id: str,
    properties: list[tuple[str, object]] | None = None,
) -> bpy.types.KeyMapItem | None:
    matches = _matching_kmis(km, op_id, properties)
    return matches[0] if matches else None


def _remove_matching_kmis(
    km: bpy.types.KeyMap | None,
    op_id: str,
    properties: list[tuple[str, object]] | None = None,
) -> int:
    if km is None:
        return 0

    removed = 0
    for kmi in list(_matching_kmis(km, op_id, properties)):
        try:
            km.keymap_items.remove(kmi)
            removed += 1
        except ReferenceError:
            pass
        except RuntimeError as exc:
            log.warning("Could not remove keymap item '%s': %s", op_id, exc)

    return removed


def _apply_kmi_properties(kmi: bpy.types.KeyMapItem, cfg: dict) -> None:
    for name, value in cfg.get("properties", []):
        setattr(kmi.properties, name, value)


def _get_effective_kmi(
    wm: bpy.types.WindowManager,
    op_id: str,
) -> tuple[
    bpy.types.KeyConfig | None,
    bpy.types.KeyMap | None,
    bpy.types.KeyMapItem | None,
    str | None,
]:
    """
    Resolve the visible keymap item for this operator.

    Order matters:
    - USER overrides ADDON
    - ADDON is the fallback default recreated on startup
    """
    cfg = KEYMAP_CONFIGS.get(op_id)
    if cfg is None:
        return None, None, None

    keymap_name = cfg.get("keymap_name")
    properties = cfg.get("properties")

    kc_user = wm.keyconfigs.user
    if kc_user is not None:
        km_user = kc_user.keymaps.get(keymap_name)
        kmi_user = _find_kmi(km_user, op_id, properties)
        if kmi_user is not None:
            return kc_user, km_user, kmi_user, "USER"

    kc_addon = wm.keyconfigs.addon
    if kc_addon is not None:
        km_addon = kc_addon.keymaps.get(keymap_name)
        kmi_addon = _find_kmi(km_addon, op_id, properties)
        if kmi_addon is not None:
            return kc_addon, km_addon, kmi_addon, "ADDON"

    return None, None, None, None


def _tag_ui_redraw() -> None:
    wm = bpy.context.window_manager
    for window in wm.windows:
        screen = window.screen
        if screen is None:
            continue

        for area in screen.areas:
            if area.type in {"PREFERENCES", "VIEW_3D"}:
                area.tag_redraw()


# ---------------------------------------------------------------------------
# UI drawing
# ---------------------------------------------------------------------------


def draw_keymap_settings(layout: bpy.types.UILayout, _prefs) -> None:
    """
    Draw keymap entries in the addon preferences panel.

    Looks up kmis from keyconfigs.user — the persisted layer — so the
    displayed state always matches what Blender has saved to userpref.blend.
    """
    wm = bpy.context.window_manager

    box = layout.box()
    box.label(text="Keymaps:")

    # Group entries by keymap_name for a tidy sectioned UI.
    groups: dict[str, list[tuple[str, dict]]] = {}
    for op_id, cfg in KEYMAP_CONFIGS.items():
        if not cfg.get("show_in_prefs", True):
            continue
        groups.setdefault(cfg["keymap_name"], []).append((op_id, cfg))

    for keymap_name, entries in groups.items():
        section = box.box()
        section.label(text=f"{keymap_name}:")

        for op_id, cfg in entries:
            kc, km, kmi, source = _get_effective_kmi(wm, op_id)

            row = section.row(align=True)

            if kc is None or km is None or kmi is None:
                split = row.split(factor=0.35, align=True)
                split.label(text=cfg["label"])
                warn = split.row(align=True)
                warn.alert = True
                warn.label(text="Missing keymap item", icon="ERROR")
                continue

            row.context_pointer_set("keymap", km)
            rna_keymap_ui.draw_kmi(["ADDON", "USER", "DEFAULT"], kc, km, kmi, row, 0)

            # If user override, restore to addon default
            if source == "USER":
                op = row.operator(
                    SimpleToolbox_OT_RestoreKeymap.bl_idname,
                    text="",
                    icon="LOOP_BACK",
                )
                op.op_id = op_id


# ---------------------------------------------------------------------------
# Restore operator
# ---------------------------------------------------------------------------


class SimpleToolbox_OT_RestoreKeymap(bpy.types.Operator):
    """Restore a disabled or missing keymap item to its addon default."""

    bl_idname = "r0tools.restore_keymap"
    bl_label = "Restore Keymap"
    bl_description = "Remove the user override and restore the addon default binding"

    op_id: StringProperty()  # type: ignore

    def execute(self, context):
        cfg = KEYMAP_CONFIGS.get(self.op_id)
        if not cfg:
            self.report({"WARNING"}, f"No config found for '{self.op_id}'")
            return {"CANCELLED"}

        wm = context.window_manager
        kc_user = wm.keyconfigs.user

        if kc_user is None:
            self.report({"WARNING"}, "User keyconfig is not available")
            return {"CANCELLED"}

        # Remove any user-layer override so the addon default shows through.
        km_user = kc_user.keymaps.get(cfg["keymap_name"])
        removed = _remove_matching_kmis(
            km_user,
            self.op_id,
            cfg.get("properties"),
        )

        _tag_ui_redraw()

        if removed:
            self.report({"INFO"}, f"Restored default keymap for '{cfg['label']}'")
        else:
            self.report({"INFO"}, f"No user override found for '{cfg['label']}'")

        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Registration / unregistration
# ---------------------------------------------------------------------------


def register_keymaps() -> None:
    """
    Register default add-on keymaps.

    The add-on layer is recreated each startup, while user edits persist in the
    user layer and override these defaults.
    """
    log.info("Register Keymaps")

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc is None:
        log.warning("No addon keyconfig available, skipping keymap registration")
        return

    _addon_keymaps.clear()

    for op_id, cfg in KEYMAP_CONFIGS.items():
        # keymaps.new() is idempotent: returns the existing km if already present.
        km = kc.keymaps.new(
            name=cfg.get("keymap_name", ""),
            space_type=cfg.get("space_type", "EMPTY"),
            region_type=cfg.get("region_type", "WINDOW"),
        )

        # Defensive cleanup for script reload / duplicate state
        _remove_matching_kmis(km, op_id, cfg.get("properties"))

        key = cfg.get("default_key", "NONE")
        value = cfg.get("value", "PRESS")

        try:
            kmi = km.keymap_items.new(op_id, type=key, value=value)
            _apply_kmi_properties(kmi, cfg)

            # Keep unbound defaults as active, "type='NONE'" is unassigned.
            _addon_keymaps.append((op_id, km, kmi))

            log.info(f"Registered keymap for '{op_id}' (type={key}, value={value=})")

        except Exception as e:
            log.error(f"Failed to register keymap for '{op_id}': {e}")


def unregister_keymaps() -> None:
    log.info("Unregister Keymaps")

    for op_id, km, kmi in reversed(_addon_keymaps):
        try:
            km.keymap_items.remove(kmi)
        except ReferenceError:
            log.debug(f"Keymap item '{op_id}' was already invalid")
        except RuntimeError as e:
            log.warning(f"Unable to remove keymap item '{op_id}': {e}")

    _addon_keymaps.clear()


# ---------------------------------------------------------------------------
# Module register / unregister
# ---------------------------------------------------------------------------

classes = [
    SimpleToolbox_OT_RestoreKeymap,
]


def register() -> None:
    for cls in classes:
        log.debug(f"Register {cls.__name__}")
        bpy.utils.register_class(cls)
    register_keymaps()


def unregister() -> None:
    unregister_keymaps()
    for cls in classes:
        log.debug(f"Unregister {cls.__name__}")
        bpy.utils.unregister_class(cls)
