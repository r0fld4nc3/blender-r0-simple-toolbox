import concurrent.futures
import re
import sys

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
    print(f"{_update_callback=}")
    if future is not None and future.done():
        result = future.result()
        print(f"{result=}")
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
