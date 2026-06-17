from typing import List

from utils.commands import RSYNC_TIMEOUT, SSH_TIMEOUT, run_command
from utils.devices_config import get_data_dir, load_devices, load_programs_list

def main():
    print("Copying programs to Raspberry Pi devices...")

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

        if not run_command(
            ["ssh", rpi, "mkdir -p /home/pi/wcl"],
            timeout=SSH_TIMEOUT,
            description=f"create /home/pi/wcl on {rpi}",
        ):
            continue

        for program in device_programs:
            print(f"Copying {program} on {rpi}")
            run_command(
                [
                    "rsync",
                    "-a",
                    "--exclude=.git",
                    f"{data_dir}/{program}",
                    f"{rpi}:/home/pi/wcl/",
                ],
                timeout=RSYNC_TIMEOUT,
                description=f"copy {program} to {rpi}",
            )

        print(f"Finished processing {rpi}")


if __name__ == "__main__":
    main()
