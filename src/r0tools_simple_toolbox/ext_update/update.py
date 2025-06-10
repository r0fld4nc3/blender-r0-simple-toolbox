import json
import re
import sys
import time
from pathlib import Path

import bpy
import requests

REQUEST_TIMEOUT = 10  # seconds

_mod = "REPO.UPDATER"


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
    from ..defines import BASE_NAME, INTERNAL_NAME, REPO_NAME, UPDATE_CHECK_CD
    from ..ui import r0Tools_PT_SimpleToolbox
    from ..utils import get_addon_fs_path, get_addon_prefs

    addon_prefs = get_addon_prefs()

    update_check_file: Path = get_addon_fs_path() / BASE_NAME / "check_update"
    if not update_check_file.exists():
        update_check_file = get_addon_fs_path() / "check_update"
    print(f"[INFO] [{_mod}] Update File: {str(update_check_file)}")

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

    if addon_prefs.check_update_startup:
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

        print(f"[INFO] [{_mod}] Now: {now:.0f}.")
        print(f"[INFO] [{_mod}] Last checked: {last_checked:.0f}.")
        print(f"[INFO] [{_mod}] Elapsed: {elapsed_since_check:.0f} seconds. (Cooldown of {UPDATE_CHECK_CD} seconds)")

        if now > can_run_after:
            is_extension = False

            if "bl_ext." in INTERNAL_NAME.lower():
                print(f"[INFO] [{_mod}] [INFO] Addon is currently loaded as Extension.")
                is_extension = True
            else:
                print(f"[INFO] [{_mod}] [INFO] Addon is currently loaded as Local.")

            if is_extension:
                remote_json = get_repo_remote_json(BASE_NAME, REPO_NAME)
                remote_version = remote_json.get("version", "0.0.0")
                has_update = check_extension_update_json(INTERNAL_NAME, remote_json)
            else:
                remote_version: str = get_repo_addon_version()
                remote_latest: tuple = tuple_version_string(remote_version)
                has_update = check_local_addon_udpate(INTERNAL_NAME, remote_latest)

            # TODO: Expand on the concept of returning None.
            # If None, means that something wasn't able to determine if
            # there was an update or not.
            if has_update is None:
                has_update = False

            update_data[KEY_LAST_CHECKED] = now
            update_data[KEY_CAN_RUN_WHEN] = now + UPDATE_CHECK_CD
            update_data[KEY_UPDATE_AVAILABLE] = has_update
            update_data[KEY_PULLED_VERSION] = remote_version

            with open(update_check_file, "w") as f:
                f.write(json.dumps(update_data))

            if has_update:
                r0Tools_PT_SimpleToolbox._update_callback(has_update)

            return has_update
        else:
            remaining_seconds = can_run_after - now
            print(f"[INFO] [{_mod}] Reading from cached file. Can retry in {abs(remaining_seconds):.0f} seconds.")
            with open(update_check_file, "r") as f:
                update_data = json.load(f)

            remote_version = tuple_version_string(update_data.get(KEY_PULLED_VERSION))
            local_version = get_local_version(INTERNAL_NAME)

            print(f"[INFO] [{_mod}] Local Version: {local_version}")
            print(f"[INFO] [{_mod}] Remote Version: {remote_version}")

            has_update = local_version < remote_version

            update_data[KEY_UPDATE_AVAILABLE] = has_update

            with open(update_check_file, "w") as f:
                f.write(json.dumps(update_data))

            r0Tools_PT_SimpleToolbox._update_callback(has_update)
        print("-------------------------------------------------------")
    else:
        print(f"[INFO] [{_mod}] Check update turned off. No update check.")

    return False


def get_repo_remote_json(addon_id: str, ext_repo_name: str) -> dict:
    # Get repository and remote_url
    repo = bpy.context.preferences.extensions.repos.get(ext_repo_name)
    metadata_url = repo.remote_url

    # Fetch JSON metadata from online repository
    try:
        print(f"[INFO] [{_mod}] Fetching matadata '{metadata_url}'.")
        response = requests.get(metadata_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        metadata = response.json()
    except Exception as e:
        print(f"[ERROR] [{_mod}] Failed to fetch or parse JSON metadata.\n{e}")
        return {}

    pulled = {}
    for ext in metadata.get("data", []):
        if ext.get("id") == addon_id:
            pulled = ext
            break

    if pulled is None or not pulled:
        print(f"[INFO] [{_mod}] No remote data foind for addon with id: '{addon_id}'.")
        return {}

    print(f"[INFO] [{_mod}] {json.dumps(pulled, indent=2)}")

    return pulled


def get_repo_addon_version() -> str:
    from ..repo import RELEASES_PAGE

    releases_latest = f"{RELEASES_PAGE}/latest"
    try:
        print(f"[INFO] [{_mod}] Fetching URL response for '{releases_latest}'.")
        response = requests.get(
            releases_latest, headers={"Content-Type": "application/vnd.github.v3+json"}, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
    except Exception as conn_err:
        print(f"[ERROR] [{_mod}] {conn_err}")

    print(f"[INFO] [{_mod}] Response: '{response.url}'.")

    release = response.url.split("/")[-1]
    if release in ["releases", "latest"]:
        release = "0.0.0"

    return version_tuple_to_str(tuple_version_string(release))


def check_extension_update_json(addon_id: str, ext_json: dict) -> bool | None:
    print(f"[INFO] [{_mod}] Checking extension update json")

    installed_version = get_local_version(addon_id)

    remote_version_str = ext_json.get("version")
    if not remote_version_str:
        print(f"[INFO] [{_mod}] Remote version information not found")
        return None

    remote_version = tuple_version_string(remote_version_str)
    print(f"[INFO] [{_mod}] Local version for '{addon_id}': {installed_version}")
    print(f"[INFO] [{_mod}] Remote version for '{addon_id}': {remote_version}")

    if installed_version < remote_version:
        print(f"[INFO] [{_mod}] Update available!")
        return True
    else:
        print(f"[INFO] [{_mod}] '{addon_id}' is up to date.")

    return False


def check_local_addon_udpate(addon_id, remote_version: tuple) -> bool | None:
    print(f"[INFO] [{_mod}] Checking local addon update")

    installed_version = get_local_version(addon_id)

    print(f"[INFO] [{_mod}] Local version for '{addon_id}': {installed_version}")
    print(f"[INFO] [{_mod}] Remote version for '{addon_id}': {remote_version}")

    if installed_version < remote_version:
        print(f"[INFO] [{_mod}] Update available!")
        return True
    else:
        print(f"[INFO] [{_mod}] '{addon_id}' is up to date.")

    return False


def get_local_version(addon_id: str) -> tuple:
    """
    Get local addon/extension version by match of provided `addon_id`
    representing the module's internal name.

    Returns `tuple`.
    """
    addon = bpy.context.preferences.addons.get(addon_id)

    if not addon:
        print(f"[INFO] [{_mod}] Addon '{addon_id}' not found. Unable to retrieve version")
        return (0, 0, 0)

    module_name = addon.module
    mod = sys.modules.get(module_name)

    if "bl_ext." in module_name.lower():
        # Reference the file that imports bl_info and makes itr available
        # defines.py works because it imports bl_info at the top so we can access it
        #
        # For some odd reason, when dealing with extensions, the info from __init__
        # isn't readily available, at least I haven't figured out a way, yet.
        mod = mod.defines

    installed_version = mod.bl_info.get("version", (0, 0, 0))
    print(f"[INFO] [{_mod}] Installed version for '{addon_id}': {installed_version}")

    return installed_version


def version_tuple_to_str(vt: tuple):
    return ".".join(str(c) for c in vt)
