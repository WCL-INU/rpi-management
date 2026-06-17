import concurrent.futures
import shlex
from typing import List

from utils.commands import SETUP_TIMEOUT, SSH_TIMEOUT, run_command
from utils.devices_config import get_data_dir, load_devices, load_programs_list

def main():
    print("Enabling programs to Raspberry Pi devices...")

    data_dir = str(get_data_dir())
    devices = load_devices()
    shared_programs: List[str] = load_programs_list(data_dir)

    if not devices:
        print("No Raspberry Pi devices found in devices.yaml.")
        return
    
    def process_rpi(rpi: str, programs: List[str]) -> None:
        rpi = rpi.strip()
        if not rpi:
            return

        print(f"Processing Raspberry Pi: {rpi}")
        if not run_command(
            ["ssh", rpi, "mkdir -p /home/pi/wcl"],
            timeout=SSH_TIMEOUT,
            description=f"create /home/pi/wcl on {rpi}",
        ):
            return

        for program_name in programs:
            if not program_name:
                continue
            print(f"Enabling {program_name} on {rpi}")
            program_dir = f"/home/pi/wcl/{program_name}"
            run_command(
                [
                    "ssh",
                    rpi,
                    f"cd {shlex.quote(program_dir)} && bash -lc 'source setup'",
                ],
                timeout=SETUP_TIMEOUT,
                description=f"enable {program_name} on {rpi}",
            )

        print(f"Finished processing {rpi}")

    tasks = []
    for device in devices:
        host = device.get("host") or device.get("id")
        programs = device.get("programs", shared_programs)
        if not host:
            print("Skipping device without host or id.")
            continue
        if not programs:
            print(f"No programs configured for {host}, skipping.")
            continue
        tasks.append((host, programs))

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(process_rpi, host, programs) for host, programs in tasks
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()


if __name__ == "__main__":
    main()
