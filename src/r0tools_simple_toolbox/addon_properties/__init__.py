import importlib

# Import order here is really important!
from .. import utils as u  # isort: skip

_mod = "ADDON PROPERTIES"

modules_load_order = (
    "edge_data_props",
    "object_sets_props",
    "vertex_groups_props",
    "find_modifiers_props",
    "export_props",
    "object_props",
    "experimental_props",
    "properties",
)

modules = [importlib.import_module(f".{name}", __package__) for name in modules_load_order]


def register():
    for mod in modules:
        if hasattr(mod, "register"):
            mod.register()
            if u.is_debug():
                print(f"[INFO] [{_mod}] Registered: {mod.__name__}")


def unregister():
    for mod in reversed(modules):
        if hasattr(mod, "unregister"):
            mod.unregister()
            if u.is_debug():
                print(f"[INFO] [{_mod}] Unregistered: {mod.__name__}")
