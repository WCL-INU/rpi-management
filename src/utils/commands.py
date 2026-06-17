from __future__ import annotations

import subprocess
from typing import Sequence


SSH_TIMEOUT = 60
RSYNC_TIMEOUT = 300
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
