import json
import logging
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

log = logging.getLogger("Settings")

_current: Optional["SettingsManager"] = None


@dataclass
class AutoSaveHookedSettingsClass:
    _manager: Optional["SettingsManager"] = field(default=None, init=False, repr=False, compare=False)

    def __setattr__(self, name: str, value):

        # Skip internal attributes
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return

        object.__setattr__(self, name, value)

        # Trigger auto-save
        if hasattr(self, "_manager") and self._manager:
            self._manager._mark_dirty()


@dataclass
class Settings(AutoSaveHookedSettingsClass):
    """Main Settings"""

    debug: bool = False

    # Update
    update_last_checked: float = 0.0
    can_update_when: float = 0.0
    update_available: bool = False
    pulled_version: str = "0.0.0"


class SettingsManager:
    def __init__(self, config_file_name: str = "r0fl_simple_toolbox_settings.json"):
        self.config_dir: Path = Path(__file__).parent
        self.config_file = self.config_dir / config_file_name
        self.settings = Settings()
        self.settings._manager = self  # Link manager to class
        self._auto_save = True
        self._dirty = False

    def _mark_dirty(self):
        """Mark settings as modified and trigger auto-save."""
        self._dirty = True
        if self._auto_save:
            self.save_settings()

    def load(self) -> bool:
        """Load from disk."""
        if not self.config_file.exists():
            log.warning(f"Config file does not exist.")
            return False

        data = self._read_json(self.config_file)
        if data:
            self.settings = self._from_dict(data)
            self._dirty = False
            log.info(f"Loaded config from '{self.config_file}")
            return True
        return False

    def save_settings(self) -> bool:
        """Save settings to disk."""
        if not self._auto_save:
            return True

        self.config_dir.mkdir(parents=True, exist_ok=True)
        data = self._to_dict(self.settings)

        if self._write_json(self.config_file, data):
            self._dirty = False
            log.info(f"Saved settings to '{self.config_file}'")
            return True
        return False

    def batch_update(self):
        return _BatchContext(self)

    def _to_dict(self, settings: Settings) -> dict:
        """Convert Settings to dict."""

        def _dict_factory(field_list):
            """Custom dict factory to filter and exclude certain attributes."""
            return {k: v for k, v in field_list if not k.startswith("_")}

        data = asdict(settings, dict_factory=_dict_factory)
        return data

    def _from_dict(self, data: dict) -> Settings:
        """Convert dict settings to Settings."""

        # Filter valid fields
        valid_fields = {k: v for k, v in data.items() if k in Settings.__annotations__}

        settings = Settings(**valid_fields)
        settings._manager = self  # Link manager class

        return settings

    def _read_json(self, fp: Path) -> Optional[dict]:
        try:
            if not fp.exists():
                return None

            content = fp.read_text(encoding="utf-8")

            if not content.strip():
                return None

            return json.loads(content)
        except json.JSONDecodeError as e:
            log.error(f"JSON Decode Error: {e}")
            backup = fp.with_suffix(fp.suffix + ".baddecode")
            shutil.copy2(fp, backup)
            log.info(f"Backed up corrupted file to: {backup}")
            return None
        except Exception as e:
            log.error(f"Error reading config: {e}")
            return None

    def _write_json(self, fp: Path, data: dict) -> bool:
        fp.parent.mkdir(parents=True, exist_ok=True)

        temp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(fp.parent), delete=False)

        try:
            temp.write(json.dumps(data, indent=2, ensure_ascii=False))
            temp.flush()
            os.fsync(temp.fileno())
            temp.close()
            shutil.move(temp.name, fp)
            return True
        except Exception as e:
            log.error(f"Error writing config: {e}")
            try:
                os.unlink(temp.name)
            except:
                pass
            return False


class _BatchContext:
    """Context manager for batch updates."""

    def __init__(self, manager: SettingsManager):
        self.manager = manager

    def __enter__(self):
        log.debug(f"Batch update started, disabling auto-save.")
        self.manager._auto_save = False
        return self.manager

    def __exit__(self, *args):
        log.debug(f"Batch update ending, dirty={self.manager._dirty}")
        self.manager._auto_save = True
        if self.manager._dirty:
            log.debug("Saving batched changes.")
            self.manager.save_settings()
        else:
            log.warning("Batch update completed without marked as dirty.")


def init_settings_manager() -> SettingsManager:
    global _current

    if _current is not None:
        if isinstance(_current, SettingsManager):
            return _current
        else:
            raise RuntimeError(f"Current instance is invalid: {_current}")

    _current = SettingsManager()
    _current.load()

    return _current


def get_settings_manager() -> SettingsManager:
    global _current

    if not isinstance(_current, SettingsManager):
        raise RuntimeError(f"Current instance is invalid: {_current}")

    if not _current or _current is None:
        raise RuntimeError(f"Settings is not valid or uninitialised: {_current}")

    return _current
