import json
import re
import sys
import time
from pathlib import Path

import bpy
import requests

UPDATER_LOG_PREFIX = "[UPDATER]"


def tuple_version_string(version_str: str):
    """
    Convert a version string like 'v1.2.3' or '1.2.3' to a tuple of ints (1, 2, 3)
    """

    # Remove leading non numeric characters
    match = re.search(r"(\d+(\.\d+)+)", version_str)
    if match:
        version_str = match.group(1)

    return tuple(int(part) for part in version_str.split("."))


def trigger_update_check(*args, **kwargs) -> bool:
    from ..const import BASE_NAME, INTERNAL_NAME, REPO_NAME, UPDATE_CHECK_CD
    from ..ui import r0Tools_PT_SimpleToolbox
    from ..utils import get_addon_fs_path, get_addon_prefs

    addon_prefs = get_addon_prefs()

    update_check_file: Path = get_addon_fs_path() / BASE_NAME / "check_update"
    print(f"[INFO] Update File: {str(update_check_file)}")

    KEY_LAST_CHECKED = "last_checked"
    KEY_CAN_RUN_WHEN = "can_run_when"
    KEY_UPDATE_AVAILABLE = "update_available"
    KEY_PULLED_VERSION = "pulled_version"

    update_data = {
        KEY_LAST_CHECKED: 0,
        KEY_CAN_RUN_WHEN: 0,
        KEY_UPDATE_AVAILABLE: False,
        KEY_PULLED_VERSION: "0.0.0",
    }

    if addon_prefs.experimental_features and addon_prefs.check_update_startup:
        print("-------------------------------------------------------")
        if update_check_file.exists() and update_check_file.is_file():
            with open(update_check_file, "r") as f:
                update_data = json.load(f)
        else:
            with open(update_check_file, "w") as f:
                f.write(json.dumps(update_data))

        now = time.time()
        last_checked = update_data.get(KEY_LAST_CHECKED)
        can_run_after = update_data.get(KEY_CAN_RUN_WHEN)
        elapsed_since_check = now - last_checked

        print(f"[INFO] Now: {now:.0f}.")
        print(f"[INFO] Last checked: {last_checked:.0f}.")
        print(f"[INFO] Elapsed: {elapsed_since_check:.0f} seconds.")

        if now > can_run_after:
            remote_json = get_remote_json(BASE_NAME, REPO_NAME)
            has_update = check_extension_update_json(INTERNAL_NAME, remote_json)

            # TODO: Expand on the concept of returning None.
            # If None, means that something wasn't able to determine if
            # there was an update or not.
            if has_update is None:
                has_update = False

            update_data[KEY_LAST_CHECKED] = now
            update_data[KEY_CAN_RUN_WHEN] = now + UPDATE_CHECK_CD
            update_data[KEY_UPDATE_AVAILABLE] = has_update
            update_data[KEY_PULLED_VERSION] = remote_json.get("version", "0.0.0")

            with open(update_check_file, "w") as f:
                f.write(json.dumps(update_data))

            if has_update:
                r0Tools_PT_SimpleToolbox._update_callback(has_update)

            return has_update
        else:
            remaining_seconds = can_run_after - now
            print(
                f"[INFO] Reading from cached file. Can retry in {abs(remaining_seconds):.0f} seconds."
            )
            with open(update_check_file, "r") as f:
                update_data = json.load(f)

            remote_version = tuple_version_string(update_data.get(KEY_PULLED_VERSION))
            local_version = get_local_version(INTERNAL_NAME)

            print(f"Local Version: {local_version}")
            print(f"Remote Version: {remote_version}")

            has_update = local_version < remote_version

            update_data[KEY_UPDATE_AVAILABLE] = has_update

            with open(update_check_file, "w") as f:
                f.write(json.dumps(update_data))

            r0Tools_PT_SimpleToolbox._update_callback(has_update)
        print("-------------------------------------------------------")
    else:
        print("Experimental features turned off. No update check.")

    return False


def get_remote_json(addon_id: str, ext_repo_name: str) -> dict:
    # Get repository and remote_url
    repo = bpy.context.preferences.extensions.repos.get(ext_repo_name)
    metadata_url = repo.remote_url

    # Fetch JSON metadata from online repository
    try:
        print(f"{UPDATER_LOG_PREFIX} [INFO] Fetching matadata '{metadata_url}'.")
        response = requests.get(metadata_url)
        response.raise_for_status()
        metadata = response.json()
    except Exception as e:
        print(
            f"{UPDATER_LOG_PREFIX} [ERROR] Failed to fetch or parse JSON metadata.\n{e}"
        )
        return {}

    pulled = {}
    for ext in metadata.get("data", []):
        if ext.get("id") == addon_id:
            pulled = ext
            break

    if pulled is None or not pulled:
        print(
            f"{UPDATER_LOG_PREFIX} [INFO] No remote data foind for addon with id: '{addon_id}'."
        )
        return {}

    print(f"{json.dumps(pulled, indent=2)}")

    return pulled


def check_extension_update_json(addon_id: str, ext_json: dict) -> bool | None:
    installed_version = get_local_version(addon_id)

    remote_version_str = ext_json.get("version")
    if not remote_version_str:
        print(f"{UPDATER_LOG_PREFIX} [INFO] Remote version information not found")
        return None

    remote_version = tuple_version_string(remote_version_str)
    print(
        f"{UPDATER_LOG_PREFIX} [INFO] Remote version for '{addon_id}': {remote_version}"
    )

    if installed_version < remote_version:
        print(f"{UPDATER_LOG_PREFIX} [INFO] Update available!")
        return True
    else:
        print(f"{UPDATER_LOG_PREFIX} [INFO] '{addon_id}' is up to date.")

    return False


def get_local_version(addon_id: str) -> tuple:
    """
    Get local addon/extension version by match of provided `addon_id`
    representing the module's internal name.

    Returns `tuple`.
    """
    addon = bpy.context.preferences.addons.get(addon_id)

    if not addon:
        print(
            f"{UPDATER_LOG_PREFIX} [INFO] Addon '{addon_id}' not found. Unable to retrieve version"
        )
        return (0, 0, 0)

    module_name = addon.module
    mod = sys.modules.get(module_name)

    if "bl_ext." in module_name.lower():
        # Reference the file that imports bl_info and makes itr available
        # const.py works because it imports bl_info at the top so we can access it
        #
        # For some odd reason, when dealing with extensions, the info from __init__
        # isn't readily available, at least I haven't figured out a way, yet.
        mod = mod.const

    installed_version = mod.bl_info.get("version", (0, 0, 0))
    print(
        f"{UPDATER_LOG_PREFIX} [INFO] Installed version for '{addon_id}': {installed_version}"
    )

    return installed_version


def version_tuple_to_str(vt: tuple):
    return ".".join(str(c) for c in vt)
