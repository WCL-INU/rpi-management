Raspberry Pi Management Scripts
===============================

This repo contains utilities to deploy programs to multiple Raspberry Pi devices, provision their `.env` files, and control services via SSH/rsync.

Setup
-----
- Requirements: Python 3.10+ and [uv](https://github.com/astral-sh/uv).
- Install deps:
  ```bash
  uv sync
  ```
- Prepare configuration under `data/` (git-ignored):
  - `data/devices.yaml`: unified inventory + env values.
    ```yaml
    devices:
      - id: raspberrypi-1          # device identifier
        host: raspberrypi-1.local  # SSH target; falls back to id if missing
        env:                         # per-device env values
          SERVER_URL: "https://..."
          HIVE_ID: 44
          SENSOR_TYPE_ID: 2
          SENSOR_DEVICE_IDs: "134 135 ..."
        programs:                    # optional per-device program list
          - sensor-uploader
    ```
  - Program sources under `data/<program>/` (copied to `/home/pi/wcl/<program>`).
  - Each program’s env template at `data/<program>/env/.env.example` lists required keys.
  - Optional fallback `data/list-of-programs` (one program name per line) used when a device has no `programs` list.
- SSH access: ensure `ssh <host>` works for each Pi (keys/config in `~/.ssh/config` as needed).

Utilities
---------
- `src/copy-programs.py`: rsync programs from `data/` to each Pi under `/home/pi/wcl/`.
- `src/enable-programs.py`: for each program, SSH and run `source setup` in `/home/pi/wcl/<program>`.
- `src/update-programs.py`: stop `upload-<program>` (systemd), rsync updated code (excludes `.git`/`.env`), then restart.
- `src/write-env-file.py`: read `devices.yaml`, match env keys from `.env.example`, and write `/home/pi/wcl/<program>/env/.env` on each Pi.

Running
-------
Use `uv run` to execute scripts directly:
```bash
uv run src/copy-programs.py
uv run src/write-env-file.py
uv run src/enable-programs.py
uv run src/update-programs.py
```
Or via `main.py`:
```bash
uv run main.py copy-programs
uv run main.py write-env-file
uv run main.py enable-programs
uv run main.py update-programs
```

Modifying devices.yaml in code
------------------------------
Helpers in `src/utils/devices_config.py`:
- `load_devices()` / `save_devices(devices)`
- `upsert_device(devices, device_id, host=..., env=..., programs=...)`
- `update_device_env(device, updates)`
- `set_device_programs(device, programs)`

Workflow tips
-------------
- Keep secrets/PII only in `data/devices.yaml` (git-ignored); commit templates like `.env.example` instead.
- If multiple devices share the same program set, leave `programs` empty in those entries and list programs in `data/list-of-programs`.
- Ensure `.env.example` keys match `env` entries in `devices.yaml` so `write-env-file` can populate values.
