import json
import logging
import re
import sys
import threading
import time
from pathlib import Path

import bpy
import requests

REQUEST_TIMEOUT = 5  # seconds

log = logging.getLogger(__name__)


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

    log.info(f"Update File: {str(update_check_file)}")

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
        log.info("-------------------------------------------------------")
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

        log.info(f"Now: {now:.0f}.")
        log.info(f"Last checked: {last_checked:.0f}.")
        log.info(f"Elapsed: {elapsed_since_check:.0f} seconds. (Cooldown of {UPDATE_CHECK_CD} seconds)")

        if now > can_run_after:
            is_extension = False

            if "bl_ext." in INTERNAL_NAME.lower():
                log.info(f"Addon is currently loaded as Extension.")
                is_extension = True
            else:
                log.info(f"Addon is currently loaded as Local.")

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
            log.info(f"Reading from cached file. Can retry in {abs(remaining_seconds):.0f} seconds.")
            with open(update_check_file, "r") as f:
                update_data = json.load(f)

            remote_version = tuple_version_string(update_data.get(KEY_PULLED_VERSION))
            local_version = get_local_version(INTERNAL_NAME)
            ThreadVars.set_local_version(local_version)

            log.info(f"Local Version: {local_version}")
            log.info(f"Remote Version: {remote_version}")

            has_update = local_version < remote_version

            update_data[KEY_UPDATE_AVAILABLE] = has_update

            with open(update_check_file, "w") as f:
                f.write(json.dumps(update_data))

            r0Tools_PT_SimpleToolbox._update_callback(has_update)
        log.info("-------------------------------------------------------")
    else:
        log.info(f"Check update turned off. No update check.")

    return False


def get_repo_remote_json(addon_id: str, ext_repo_name: str) -> dict:
    # Get repository and remote_url
    repo = bpy.context.preferences.extensions.repos.get(ext_repo_name)
    metadata_url = repo.remote_url

    # Fetch JSON metadata from online repository
    try:
        log.info(f"Fetching matadata '{metadata_url}'.")
        response = requests.get(metadata_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        metadata = response.json()
    except Exception as e:
        log.error(f"Failed to fetch or parse JSON metadata.\n{e}")
        return {}

    pulled = {}
    for ext in metadata.get("data", []):
        if ext.get("id") == addon_id:
            pulled = ext
            break

    if pulled is None or not pulled:
        log.info(f"No remote data foind for addon with id: '{addon_id}'.")
        return {}

    log.info(f"{json.dumps(pulled, indent=2)}")

    return pulled


def get_repo_addon_version() -> str:
    from ..repo import RELEASES_PAGE

    releases_latest = f"{RELEASES_PAGE}/latest"
    try:
        log.info(f"Fetching URL response for '{releases_latest}'.")
        response = requests.get(
            releases_latest, headers={"Content-Type": "application/vnd.github.v3+json"}, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
    except Exception as conn_err:
        log.error(f"{conn_err}")

    log.info(f"Response: '{response.url}'.")

    release = response.url.split("/")[-1]
    if release in ["releases", "latest"]:
        release = "0.0.0"

    return version_tuple_to_str(tuple_version_string(release))


def check_extension_update_json(addon_id: str, ext_json: dict) -> bool | None:
    log.info(f"Checking extension update json")

    installed_version = get_local_version(addon_id)

    remote_version_str = ext_json.get("version")
    if not remote_version_str:
        log.info(f"Remote version information not found")
        return None

    remote_version = tuple_version_string(remote_version_str)
    log.info(f"Local version for '{addon_id}': {installed_version}")
    log.info(f"Remote version for '{addon_id}': {remote_version}")

    if installed_version < remote_version:
        log.info(f"Update available!")
        return True
    else:
        log.info(f"'{addon_id}' is up to date.")

    return False


def check_local_addon_udpate(addon_id, remote_version: tuple) -> bool | None:
    log.info(f"Checking local addon update")

    installed_version = get_local_version(addon_id)

    log.info(f"Local version for '{addon_id}': {installed_version}")
    log.info(f"Remote version for '{addon_id}': {remote_version}")

    if installed_version < remote_version:
        log.info(f"Update available!")
        return True
    else:
        log.info(f"'{addon_id}' is up to date.")

    return False


def get_local_version(addon_id: str) -> tuple:
    """
    Get local addon/extension version by match of provided `addon_id`
    representing the module's internal name.

    Returns `tuple`.
    """
    addon = bpy.context.preferences.addons.get(addon_id)

    if not addon:
        log.info(f"Addon '{addon_id}' not found. Unable to retrieve version")
        return (0, 0, 0)

    module_name = addon.module
    mod = sys.modules.get(module_name)

    if "bl_ext." in module_name.lower():
        # Reference the file that imports bl_info and makes it available
        # defines.py works because it imports bl_info at the top so we can access it
        #
        # For some odd reason, when dealing with extensions, the info from __init__
        # isn't readily available, at least I haven't figured out a way, yet.
        mod = mod.defines

    installed_version = mod.bl_info.get("version", (0, 0, 0))
    log.info(f"Installed version for '{addon_id}': {installed_version}")

    return installed_version


def version_tuple_to_str(vt: tuple):
    return ".".join(str(c) for c in vt)


#################
### THREADING ###
#################


class ThreadVars:
    _lock = threading.Lock()
    _local_version = (0, 0, 0)

    @classmethod
    def set_local_version(cls, version: tuple):
        with cls._lock:
            cls._local_version = version

    @classmethod
    def get_local_version(cls) -> tuple:
        with cls._lock:
            return cls._local_version


def _execute_callback_on_main_thread(has_update: bool):
    """
    Execute the update callback on the main thread.
    Must be called using bpy.app.timers from worker thread.
    """

    from ..ui import r0Tools_PT_SimpleToolbox

    try:
        r0Tools_PT_SimpleToolbox._update_callback(has_update)
    except Exception as e:
        log.error(f"Failed to execute update callback: {e}")

    # Stop timer
    return None


def _run_update_check_thread(
    update_check_file: Path,
    internal_name: str,
    base_name: str,
    repo_name: str,
    is_extension: bool,
    update_check_cd: int,
):
    """
    Function to run on the separate thread to check for addon updates.
    """

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

    try:
        if update_check_file.exists() and update_check_file.is_file():
            with open(update_check_file, "r") as f:
                update_data = json.load(f)

        now = time.time()
        last_checked = update_data.get(KEY_LAST_CHECKED)
        can_run_after = update_data.get(KEY_CAN_RUN_WHEN)
        elapsed_since_check = now - last_checked

        log.info(f"Now: {now:.0f}.")
        log.info(f"Last checked: {last_checked:.0f}.")
        log.info(f"Elapsed: {elapsed_since_check:.0f} seconds. (Cooldown of {update_check_cd} seconds)")

        if now > can_run_after:
            if is_extension:
                remote_json = _get_repo_remote_json_threadsafe(base_name, repo_name)
                remote_version = remote_json.get("version", "0.0.0")
                has_update = _check_extension_update_json_threadsafe(internal_name, remote_json)
            else:
                remote_version: str = get_repo_addon_version()
                remote_latest: tuple = tuple_version_string(remote_version)
                has_update = _check_local_addon_update_threadsafe(internal_name, remote_latest)

            if has_update is None:
                has_update = False

            # Update Cache file
            update_data[KEY_LAST_CHECKED] = now
            update_data[KEY_CAN_RUN_WHEN] = now + update_check_cd
            update_data[KEY_UPDATE_AVAILABLE] = has_update
            update_data[KEY_PULLED_VERSION] = remote_version

            with open(update_check_file, "w") as f:
                f.write(json.dumps(update_data))

            bpy.app.timers.register(lambda: _execute_callback_on_main_thread(has_update), first_interval=0.1)
        else:
            # Read from cache
            remaining_seconds = can_run_after - now
            log.info(f"Reading from cached file. Can retry in {abs(remaining_seconds):.0f} seconds.")

            with open(update_check_file, "r") as f:
                update_data = json.load(f)

            remote_version = tuple_version_string(update_data.get(KEY_PULLED_VERSION))
            local_version = ThreadVars.get_local_version()

            log.info(f"Local Version: {local_version}")
            log.info(f"Remote Version: {remote_version}")

            has_update = remote_version > local_version
            update_data[KEY_UPDATE_AVAILABLE] = has_update

            with open(update_check_file, "w") as f:
                f.write(json.dumps(update_data))

            bpy.app.timers.register(lambda: _execute_callback_on_main_thread(has_update), first_interval=0.1)
    except Exception as e:
        log.error(f"Update check thread error: {e}")
        bpy.app.timers.register(lambda: _execute_callback_on_main_thread(False), first_interval=0.1)

    log.info("-------------------------------------------------------")


def trigger_thread_update_check(*args, force: bool = False, **kwargs) -> bool:
    """
    Function to trigger threaded update check.
    Sets up required main-thread data before proceeding.
    """

    from ..defines import BASE_NAME, INTERNAL_NAME, REPO_NAME, UPDATE_CHECK_CD
    from ..utils import get_addon_fs_path, get_addon_prefs

    addon_prefs = get_addon_prefs()

    if not force and not addon_prefs.check_update_startup:
        log.info(f"Check update turned off. No update check.")
        return False

    log.info("-------------------------------------------------------")

    try:
        # Prepare bpy data before thread access
        update_check_file: Path = get_addon_fs_path() / BASE_NAME / "check_update"
        if not update_check_file.exists():
            update_check_file = get_addon_fs_path() / "check_update"
        log.info(f"Update File: {str(update_check_file)}")

        # Check if it's Extension
        is_extension = "bl_ext." in INTERNAL_NAME.lower()
        if is_extension:
            log.info(f"Addon is currently loaded as Extension.")
        else:
            log.info(f"Addon is currently loaded as Local.")

        repo_data = REPO_NAME
        if is_extension:
            repo = bpy.context.preferences.extensions.repos.get(REPO_NAME)
            if repo:
                repo_data = {"remote_url": repo.remote_url, "name": REPO_NAME}

        # Store local version before threading
        local_version = get_local_version(INTERNAL_NAME)
        ThreadVars.set_local_version(local_version)
        log.info(f"Stored local version: {local_version}")

        thread = threading.Thread(
            target=_run_update_check_thread,
            args=(
                update_check_file,
                INTERNAL_NAME,
                BASE_NAME,
                repo_data,
                is_extension,
                UPDATE_CHECK_CD,
            ),
            daemon=True,
        )
        thread.start()
    except Exception as e:
        log.error(f"Failed to start update check thread: {e}")

    # Return immediately without blocking
    return False


def _get_repo_remote_json_threadsafe(addon_id: str, repo_data: dict) -> dict:
    """
    Thread-safe version of get_repo_remote_json.
    Uses pre-fetched repository data instead of accessing bpy.
    """
    if isinstance(repo_data, str):
        # Legacy mode, can't fetch without bpy access
        log.warning(f"Repository data not available for threaded check")
        return {}

    metadata_url = repo_data.get("remote_url")
    if not metadata_url:
        log.error(f"No remote URL in repository data")
        return {}

    try:
        log.info(f"Fetching metadata '{metadata_url}'")
        response = requests.get(metadata_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        metadata = response.json()
    except requests.exceptions.RequestException as e:
        log.error(f"Failed to fetch metadata: {e}")
        return {}
    except json.JSONDecodeError as e:
        log.error(f"Failed to parse JSON metadata: {e}")
        return {}

    pulled = {}
    for ext in metadata.get("data", []):
        if ext.get("id") == addon_id:
            pulled = ext
            break

    if not pulled:
        log.info(f"No remote data found for addon with id: '{addon_id}'.")
        return {}

    log.info(f"{json.dumps(pulled, indent=2)}")
    return pulled


def _check_extension_update_json_threadsafe(addon_id: str, ext_json: dict) -> bool | None:
    """
    Thread-safe version of check_extension_update_json.
    """

    log.info(f"Checking extension update json")

    installed_version = ThreadVars.get_local_version()

    remote_version_str = ext_json.get("version")
    if not remote_version_str:
        log.info(f"Remote version information not found")
        return None

    remote_version = tuple_version_string(remote_version_str)
    log.info(f"Local version for '{addon_id}': {installed_version}")
    log.info(f"Remote version for '{addon_id}': {remote_version}")

    if remote_version > installed_version:
        log.info(f"Update available!")
        return True
    else:
        log.info(f"'{addon_id}' is up to date.")

    return False


def _check_local_addon_update_threadsafe(addon_id: str, remote_version: tuple) -> bool | None:
    """
    Thread-safe version of check_local_addon_update.
    """
    log.info(f"Checking local addon update")

    installed_version = ThreadVars.get_local_version()

    log.info(f"Local version for '{addon_id}': {installed_version}")
    log.info(f"Remote version for '{addon_id}': {remote_version}")

    if remote_version > installed_version:
        log.info(f"Update available!")
        return True
    else:
        log.info(f"'{addon_id}' is up to date.")

    return False
