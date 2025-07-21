import bpy


def get_boxcutter_props():
    scene = bpy.context.scene

    bc = getattr(scene, "bc", None)

    return bc


def boxcutter_running() -> bool:
    bc = get_boxcutter_props()

    if not bc:
        return False

    return bc.running
