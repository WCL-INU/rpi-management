from __future__ import annotations

import subprocess
from typing import Sequence


SSH_TIMEOUT = 60
SCP_TIMEOUT = 300
RSYNC_TIMEOUT = 300
SCRIPT_TIMEOUT = 900
SETUP_TIMEOUT = 1800


def run_command(
    cmd: Sequence[object],
    *,
    timeout: int,
    description: str,
    input_text: str | None = None,
) -> bool:
    """Run a command with timeout and print useful failure details."""
    command = [str(part) for part in cmd]
    try:
        result = subprocess.run(
            command,
            input=input_text,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"Timed out after {timeout}s: {description}")
        print(f"Command: {' '.join(command)}")
        return False

    if result.returncode == 0:
        return True

    print(f"Failed ({result.returncode}): {description}")
    print(f"Command: {' '.join(command)}")
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    return False


def run_command_capture(
    cmd: Sequence[object],
    *,
    timeout: int,
    description: str,
) -> tuple[int, str, str]:
    """Run a command with timeout and return returncode/stdout/stderr."""
    command = [str(part) for part in cmd]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        message = f"Timed out after {timeout}s: {description}"
        return 124, "", message

    return result.returncode, result.stdout or "", result.stderr or ""
