from typing import List

from utils.commands import RSYNC_TIMEOUT, SSH_TIMEOUT, run_command
from utils.devices_config import get_data_dir, load_devices, load_programs_list

def main():
    print("Updating programs on Raspberry Pi devices...")

    data_dir = str(get_data_dir())
    devices = load_devices()
    shared_programs: List[str] = load_programs_list(data_dir)

    if not devices:
        print("No Raspberry Pi devices found in devices.yaml.")
        return

    for device in devices:
        rpi = device.get("host") or device.get("id")
        if not rpi:
            print("Skipping device without host or id.")
            continue

        device_programs = device.get("programs", shared_programs)
        if not device_programs:
            print(f"No programs configured for {rpi}, skipping.")
            continue

        print(f"Processing Raspberry Pi: {rpi}")

        for program in device_programs:

            # 해당 라즈베리파이에서 서비스 동작 중지
            run_command(
                ["ssh", rpi, f"sudo systemctl stop upload-{program}"],
                timeout=SSH_TIMEOUT,
                description=f"stop upload-{program} on {rpi}",
            )
            print(f"Copying {program} on {rpi}")
            copied = run_command(
                [
                    "rsync",
                    "-a",
                    "--exclude=.git",
                    "--exclude=.env",
                    f"{data_dir}/{program}",
                    f"{rpi}:/home/pi/wcl/",
                ],
                timeout=RSYNC_TIMEOUT,
                description=f"copy {program} to {rpi}",
            )
            if not copied:
                continue
            # 해당 라즈베리파이에서 서비스 재시작
            run_command(
                ["ssh", rpi, f"sudo systemctl start upload-{program}"],
                timeout=SSH_TIMEOUT,
                description=f"start upload-{program} on {rpi}",
            )

        print(f"Finished processing {rpi}")


if __name__ == "__main__":
    main()
