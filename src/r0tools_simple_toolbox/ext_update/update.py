import concurrent.futures
import json
import re
import sys
import time
from pathlib import Path

import bpy
import requests

UPDATER_LOG_PREFIX = "[UPDATER]"

# Create a global executor
executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
future = None
_update_callback = None  # Global callback variable


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
    from ..const import INTERNAL_NAME, REPO_NAME, UPDATE_CHECK_CD
    from ..ui import r0Tools_PT_SimpleToolbox
    from ..utils import get_addon_fs_path, get_addon_prefs

    addon_prefs = get_addon_prefs()

    update_check_file: Path = get_addon_fs_path() / INTERNAL_NAME / "check_update"
    print(f"[INFO] Update File: {str(update_check_file)}")

    KEY_LAST_CHECKED = "last_checked"
    KEY_CAN_RUN_WHEN = "can_run_when"
    KEY_UPDATE_AVAILABLE = "update_available"

    update_data = {
        KEY_LAST_CHECKED: 0,
        KEY_CAN_RUN_WHEN: 0,
        KEY_UPDATE_AVAILABLE: False,
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
            has_update = check_extension_update_json(INTERNAL_NAME, REPO_NAME)

            if has_update is None:
                has_update = False

            update_data[KEY_LAST_CHECKED] = now
            update_data[KEY_CAN_RUN_WHEN] = now + UPDATE_CHECK_CD
            update_data[KEY_UPDATE_AVAILABLE] = has_update

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

            has_update = update_data.get(KEY_UPDATE_AVAILABLE)

            r0Tools_PT_SimpleToolbox._update_callback(has_update)
        print("-------------------------------------------------------")
    else:
        print("Experimental features turned off. No update check.")

    return False


def check_extension_update_json(addon_id: str, ext_repo_name: str) -> bool | None:
    addon = bpy.context.preferences.addons.get(addon_id)

    if not addon:
        print(f"{UPDATER_LOG_PREFIX} [INFO] Addon '{addon_id}' not found.")
        return None
    else:
        print(f"{UPDATER_LOG_PREFIX} [INFO] Addon '{addon_id}'.")

    mod = sys.modules[addon_id]
    installed_version = mod.bl_info.get("version", (0, 0, 0))
    if isinstance(installed_version, (list, tuple)):
        installed_version = tuple(installed_version)
    else:
        installed_version = tuple_version_string(installed_version)

    print(
        f"{UPDATER_LOG_PREFIX} [INFO] Installed version for '{addon_id}': {installed_version}"
    )

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
        return None

    remote_extension = None
    for ext in metadata.get("data", []):
        if ext.get("id") == addon_id:
            remote_extension = ext
            break

    if remote_extension is None:
        print(
            f"{UPDATER_LOG_PREFIX} [INFO] No remote data foind for addon with id: '{addon_id}'."
        )
        return None

    remote_version_str = remote_extension.get("version")
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


def poll_future():
    """
    Polls the global future. When done, process the result.
    Returns None to stop the timer if done, or a float (seconds) to poll again)
    """

    global _update_callback
    if future is not None and future.done():
        result = future.result()
        if _update_callback is not None:
            _update_callback(result)
        return None
    return 0.5


def async_check_update(addon_id: str, ext_repo_name: str, callback_func=None):
    """
    Submits the update check function to the thread pool and starts a timer to poll for its result.
    """

    global future, _update_callback

    if callback_func:
        _update_callback = callback_func

    future = executor.submit(check_extension_update_json, addon_id, ext_repo_name)
    bpy.app.timers.register(poll_future, first_interval=0.5)
