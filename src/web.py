from __future__ import annotations

import argparse
import concurrent.futures
import json
import mimetypes
import socket
import subprocess
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Iterable, List, MutableMapping, Optional
from urllib.parse import unquote, urlparse

from utils.devices_config import load_devices


ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "web"

# Keep the status check short. This page is meant to answer "is it alive?" quickly,
# so a slow or unreachable Raspberry Pi should not hold the whole dashboard hostage.
STATUS_TIMEOUT = 10
CONNECT_TIMEOUT = 4


# The main dashboard intentionally exposes only identity and network target fields.
# Program names, env keys, and CLI commands belong to a future settings page, not the
# operational status page the user asked for.
def normalize_device(device: MutableMapping[str, object]) -> Dict[str, Any]:
    device_id = str(device.get("id") or "").strip()
    host = str(device.get("host") or device_id).strip()
    return {
        "id": device_id,
        "host": host,
        "ip": resolve_ip(host),
    }


# IP resolution is useful context for operators, but it should never make the page
# fail. If mDNS/DNS cannot resolve a host, the dashboard simply shows a dash.
def resolve_ip(host: str) -> str:
    if not host:
        return ""
    try:
        return socket.gethostbyname(host)
    except OSError:
        return ""


# Devices still come from devices.yaml because that is the existing source of truth.
# This function deliberately strips all configuration-heavy fields before returning
# data to the browser.
def list_dashboard_devices() -> List[Dict[str, Any]]:
    return [normalize_device(device) for device in load_devices()]


# Initial page load is cheap and read-only: it only tells the browser which devices
# are known. Actual SSH checks are triggered separately by the user.
def devices_payload() -> Dict[str, Any]:
    devices = list_dashboard_devices()
    return {
        "devices": devices,
        "deviceCount": len(devices),
    }


# The remote command is intentionally narrow and line-oriented. Each helper prints
# exactly one key=value line. That shape matters because the browser only receives
# parsed fields, and partial command failures should not hide other healthy values.
# Camera detection uses rpicam-hello first because current Raspberry Pi OS camera
# stacks expose cameras through rpicam rather than the older libcamera command name.
def build_status_command() -> str:
    return r'''
print_value() {
  key="$1"
  shift
  value="$($@ 2>/dev/null || true)"
  printf '%s=%s\n' "$key" "$value"
}

print_value hostname hostname
print_value uptime uptime -p

ram_value="$(free -m 2>/dev/null | awk '/Mem:/ {printf "%sMB / %sMB", $3, $2}')"
printf 'ram=%s\n' "${ram_value:-unknown}"

storage_value="$(df -h / 2>/dev/null | awk 'NR==2 {printf "%s / %s (%s used)", $3, $2, $5}')"
printf 'storage=%s\n' "${storage_value:-unknown}"

if command -v rpicam-hello >/dev/null 2>&1; then
  camera_output="$(timeout 5 rpicam-hello --list-cameras 2>&1 || true)"
  if printf '%s' "$camera_output" | grep -Eiq 'Available cameras|^[[:space:]]*[0-9]+[[:space:]]*:'; then
    printf 'camera=camera available\n'
  else
    printf 'camera=not detected\n'
  fi
elif command -v libcamera-hello >/dev/null 2>&1; then
  camera_output="$(timeout 5 libcamera-hello --list-cameras 2>&1 || true)"
  if printf '%s' "$camera_output" | grep -Eiq 'Available cameras|^[[:space:]]*[0-9]+[[:space:]]*:'; then
    printf 'camera=camera available\n'
  else
    printf 'camera=not detected\n'
  fi
elif command -v vcgencmd >/dev/null 2>&1; then
  camera_value="$(vcgencmd get_camera 2>/dev/null || true)"
  printf 'camera=%s\n' "${camera_value:-unknown}"
else
  printf 'camera=unknown\n'
fi
'''.strip()


# Run one SSH status check. Failures are represented as data instead of exceptions
# so the rest of the dashboard can still render normally.
def check_device_status(device: Dict[str, Any]) -> Dict[str, Any]:
    host = device.get("host") or device.get("id") or ""
    checked_at = time.time()
    command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={CONNECT_TIMEOUT}",
        host,
        build_status_command(),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=STATUS_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "id": device["id"],
            "online": False,
            "checkedAt": checked_at,
            "error": "SSH status check timed out.",
        }

    info: Dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            info[key.strip()] = value.strip()

    return {
        "id": device["id"],
        "online": result.returncode == 0,
        "checkedAt": checked_at,
        "hostname": info.get("hostname", ""),
        "uptime": info.get("uptime", ""),
        "ram": info.get("ram", ""),
        "storage": info.get("storage", ""),
        "camera": normalize_camera_status(info.get("camera", "")),
        "error": "" if result.returncode == 0 else (result.stderr or "SSH connection failed.").strip(),
    }


# Old Raspberry Pi camera tooling returns values such as "supported=1 detected=1".
# Normalize that into dashboard-friendly text while preserving unknown/newer output.
def normalize_camera_status(raw_status: str) -> str:
    status = raw_status.strip()
    if not status:
        return "unknown"
    lower = status.lower()
    if "detected=1" in lower or "camera available" in lower:
        return "camera available"
    if "detected=0" in lower or "not detected" in lower:
        return "not detected"
    return status


# Check devices concurrently with a small cap. This keeps the manual refresh snappy
# without creating a stampede of SSH processes on larger local networks.
def status_payload() -> Dict[str, Any]:
    devices = list_dashboard_devices()
    if not devices:
        return {"statuses": [], "checkedAt": time.time()}
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(devices))) as executor:
        statuses = list(executor.map(check_device_status, devices))
    return {"statuses": statuses, "checkedAt": time.time()}


# Tiny JSON helper for the small stdlib HTTP server. Keeping it here avoids pulling
# in a web framework before the feature needs one.
def read_json(handler: BaseHTTPRequestHandler) -> Any:
    length = int(handler.headers.get("content-length") or "0")
    if length == 0:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


def send_json(handler: BaseHTTPRequestHandler, payload: Any, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("content-type", "application/json; charset=utf-8")
    handler.send_header("content-length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def send_error_json(handler: BaseHTTPRequestHandler, message: str, status: int = 400) -> None:
    send_json(handler, {"error": message}, status)


class WebHandler(BaseHTTPRequestHandler):
    server_version = "RpiManagementWeb/0.1"

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/devices":
            send_json(self, devices_payload())
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            read_json(self)
            if parsed.path == "/api/status":
                send_json(self, status_payload())
                return
            send_error_json(self, "Unknown API endpoint.", HTTPStatus.NOT_FOUND)
        except json.JSONDecodeError:
            send_error_json(self, "Invalid JSON payload.")
        except Exception as exc:
            send_error_json(self, f"Request failed: {exc}", 500)

    # Static serving is constrained to WEB_DIR so a crafted URL cannot read files
    # elsewhere in the repository.
    def serve_static(self, request_path: str) -> None:
        relative = unquote(request_path).lstrip("/") or "index.html"
        if relative.startswith(".."):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        path = (WEB_DIR / relative).resolve()
        if path != WEB_DIR and WEB_DIR not in path.parents:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if path.is_dir():
            path = path / "index.html"
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), WebHandler)
    print(f"Raspberry Pi management web UI: http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping web UI.")
    finally:
        server.server_close()


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run Raspberry Pi management web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    args = parser.parse_args(list(argv) if argv is not None else None)
    run(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
