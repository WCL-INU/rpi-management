from __future__ import annotations

import concurrent.futures
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from utils.devices_config import get_data_dir, load_devices


def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    """Run command, capture stdout/stderr"""
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def collect_notable(*outputs: str) -> List[str]:
    """Extract lines that look like warnings/errors."""
    keywords = ("error", "warn", "fail")
    notable: List[str] = []
    for output in outputs:
        for line in (output or "").splitlines():
            lower = line.lower()
            if any(key in lower for key in keywords):
                notable.append(line.strip())
    return notable


def process_device(
    device: Dict[str, object], data_dir: Path, script_path: Path
) -> Tuple[str, bool]:
    device_id: Optional[str] = device.get("id")
    host: Optional[str] = device.get("host") or device_id
    if not host:
        return ("Skipping device without host or id.", False)

    name = device_id or host
    logs: List[str] = []

    remote_script = "/tmp/run-script.py"
    rc, out, err = run_cmd(
        ["scp", "-o", "BatchMode=yes", str(script_path), f"{host}:{remote_script}"]
    )
    logs.extend(collect_notable(out, err))
    if rc != 0:
        return (f"{name}: failed to copy script to {host}", False)

    rc, out, err = run_cmd(
        ["ssh", "-o", "BatchMode=yes", host, f"python3 {remote_script}"]
    )
    logs.extend(collect_notable(out, err))
    if rc != 0:
        return (f"{name}: failed to execute script on {host}", False)

    # Fetch outputs manifest (unique local path to avoid clashes in parallel runs)
    local_manifest = Path(tempfile.gettempdir()) / f"script_outputs_{name}.json"
    rc, out, err = run_cmd(
        [
            "scp",
            "-o",
            "BatchMode=yes",
            f"{host}:/tmp/script_outputs.json",
            str(local_manifest),
        ]
    )
    logs.extend(collect_notable(out, err))
    if rc != 0 or not local_manifest.exists():
        return (
            f"{name}: failed to retrieve /tmp/script_outputs.json from {host}",
            False,
        )

    try:
        manifest = json.loads(local_manifest.read_text(encoding="utf-8"))
        files = manifest.get("files") or []
        if isinstance(files, str):
            files = [files]
        if not isinstance(files, list):
            raise ValueError("files is not a list or string")
    except Exception as exc:
        return (f"{name}: invalid manifest from {host}: {exc}", False)

    dest_dir = data_dir / "images"
    dest_dir.mkdir(parents=True, exist_ok=True)

    success = True
    for path in files:
        path_str = str(path)
        if not path_str:
            continue
        filename = os.path.basename(path_str)
        dest_path = dest_dir / filename
        rc, out, err = run_cmd(
            ["scp", "-o", "BatchMode=yes", f"{host}:{path_str}", str(dest_path)]
        )
        logs.extend(collect_notable(out, err))
        if rc != 0:
            logs.append(f"{name}: failed to retrieve {path_str} from {host}")
            success = False

    if logs:
        return ("\n".join(logs), success)
    return ("done", success)


def main() -> None:
    data_dir = get_data_dir()
    script_path = data_dir / "script.py"

    if not script_path.exists():
        print(f"Script not found: {script_path}")
        return

    devices = load_devices()
    if not devices:
        print("No devices found in devices.yaml.")
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(process_device, device, data_dir, script_path): device
            for device in devices
        }
        summaries = []
        pending = set(futures.keys())
        start = time.time()
        heartbeat = 10  # seconds

        while pending:
            done, pending = concurrent.futures.wait(
                pending,
                timeout=heartbeat,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            for future in done:
                msg, ok = future.result()
                summaries.append((futures[future].get("id"), msg, ok))
            if pending:
                elapsed = int(time.time() - start)
                print(
                    f"[running] {len(pending)} device(s) remaining... {elapsed}s elapsed",
                    flush=True,
                )

    # Condensed output after all tasks to avoid interleaving noisy logs
    for device_id, msg, ok in sorted(summaries):
        if msg and msg != "done":
            print(f"Device {device_id}:\n{msg}\n")
        if ok and (not msg or msg == "done"):
            continue


if __name__ == "__main__":
    main()
