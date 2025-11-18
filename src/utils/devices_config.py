from __future__ import annotations

from pathlib import Path
from typing import Dict, List, MutableMapping, Optional

import yaml


def get_data_dir() -> Path:
    """Return absolute path to the data directory."""
    return Path(__file__).resolve().parent.parent.parent / "data"


DEFAULT_DEVICES_PATH = get_data_dir() / "devices.yaml"


def load_devices(
    path: Optional[Path | str] = None,
) -> List[MutableMapping[str, object]]:
    """Load devices list from devices.yaml."""
    target = Path(path) if path else DEFAULT_DEVICES_PATH
    if not target.exists():
        return []

    content = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if isinstance(content, dict):
        devices = content.get("devices") or []
        if isinstance(devices, list):
            return devices
    return []


def save_devices(
    devices: List[MutableMapping[str, object]], path: Optional[Path | str] = None
) -> Path:
    """Persist devices list to devices.yaml."""
    target = Path(path) if path else DEFAULT_DEVICES_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"devices": devices}
    target.write_text(
        yaml.safe_dump(
            payload, sort_keys=False, allow_unicode=True, default_flow_style=False
        ),
        encoding="utf-8",
    )
    return target


def get_device(
    devices: List[MutableMapping[str, object]], device_id: str
) -> Optional[MutableMapping[str, object]]:
    """Find a device by id."""
    for device in devices:
        if device.get("id") == device_id:
            return device
    return None


def upsert_device(
    devices: List[MutableMapping[str, object]],
    device_id: str,
    *,
    host: Optional[str] = None,
    env: Optional[Dict[str, object]] = None,
    programs: Optional[List[str]] = None,
) -> MutableMapping[str, object]:
    """Ensure a device exists, optionally updating host/env/programs."""
    device = get_device(devices, device_id)
    if device is None:
        device = {"id": device_id}
        devices.append(device)

    if host:
        device["host"] = host
    if env:
        device_env = device.setdefault("env", {})
        device_env.update(env)
    if programs is not None:
        device["programs"] = programs
    return device


def update_device_env(
    device: MutableMapping[str, object], updates: Dict[str, object]
) -> None:
    """Merge env updates into a single device entry."""
    env_section = device.setdefault("env", {})
    env_section.update(updates)


def set_device_programs(
    device: MutableMapping[str, object], programs: List[str]
) -> None:
    """Replace the programs list for a device."""
    device["programs"] = programs


def load_programs_list(data_dir: Optional[Path | str] = None) -> List[str]:
    """Load fallback program list from data/list-of-programs."""
    base = Path(data_dir) if data_dir else get_data_dir()
    path = base / "list-of-programs"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as file:
        return [line.strip() for line in file.readlines() if line.strip()]
