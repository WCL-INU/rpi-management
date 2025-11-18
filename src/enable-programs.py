import os
import concurrent.futures
from typing import List

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
        os.system(f"ssh {rpi} 'mkdir -p /home/pi/wcl'")
        for program_name in programs:
            if not program_name:
                continue
            print(f"Enabling {program_name} on {rpi}")
            os.system(f"ssh {rpi} 'cd /home/pi/wcl/{program_name} && source setup'")

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
        for host, programs in tasks:
            executor.submit(process_rpi, host, programs)


if __name__ == "__main__":
    main()
