import logging

import bpy

from . import utils as u

log = logging.getLogger(__name__)

is_saving = False
is_updating = False  # Check if our depsgraph update is running


@bpy.app.handlers.persistent
def handler_on_save_pre(dummy):
    """Set the save lock before a file is saved."""
    global is_saving
    is_saving = True


@bpy.app.handlers.persistent
def handler_on_save_post(dummy):
    """Clear the save lock after a file is saved."""
    global is_saving
    is_saving = False


depsgraph_handlers = []

load_post_handlers = [u.refresh_object_sets_colours]

save_pre_handlers = [handler_on_save_pre]
save_post_handlers = [handler_on_save_post]


def register():
    for handler in depsgraph_handlers:
        if handler not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(handler)
            log.debug(f"Registered depsgraph handler: {handler.__name__}")

    for handler in save_pre_handlers:
        if handler not in bpy.app.handlers.save_pre:
            bpy.app.handlers.save_pre.append(handler)
            log.debug(f"Registered save_pre handler: {handler.__name__}")

    for handler in save_post_handlers:
        if handler not in bpy.app.handlers.save_post:
            bpy.app.handlers.save_post.append(handler)
            log.debug(f"Registered save_post handler: {handler.__name__}")

    for handler in load_post_handlers:
        if handler not in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.append(handler)
            log.debug(f"Registered load_post handler: {handler.__name__}")


def unregister():
    for handler in depsgraph_handlers:
        if handler in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(handler)

    for handler in save_pre_handlers:
        if handler in bpy.app.handlers.save_pre:
            bpy.app.handlers.save_pre.remove(handler)

    for handler in save_post_handlers:
        if handler in bpy.app.handlers.save_post:
            bpy.app.handlers.save_post.remove(handler)

    for handler in load_post_handlers:
        if handler in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(handler)
