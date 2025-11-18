import os
from typing import Dict, List

from utils.devices_config import get_data_dir, load_devices, load_programs_list


def extract_keywords(env_lines):
    keywords = []
    for line in env_lines:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key = line.split("=", 1)[0].strip()
            keywords.append(key)
    return keywords

def main():
    print("Writing environment file...")
    data_dir = get_data_dir()
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

        env_data: Dict[str, object] = device.get("env", {})
        print(f"Processing Raspberry Pi: {rpi}")

        # 각 프로그램 별로 .env 파일 작성
        for program in device_programs:
            program = program.strip()
            if not program:
                continue

            print(f" - {program}")
            env_example_path = data_dir / program / "env" / ".env.example"
            keywords: List[str] = []
            if env_example_path.exists():
                with open(env_example_path, "r", encoding="utf-8") as env_file:
                    env_lines = env_file.readlines()
                keywords = extract_keywords(env_lines)
                print(f"   Keywords: {keywords}")
            else:
                print(f"   .env.example not found for {program}")

            if keywords:
                env_contents = "\n".join(
                    f"{key}={env_data[key]}" for key in keywords if key in env_data
                )
                if not env_contents:
                    print(f"   No matching env values for {program}, skipping write.")
                    continue
                print(f"   Writing .env with contents:\n{env_contents}\n")
                os.system(f"ssh {rpi} 'mkdir -p /home/pi/wcl/{program}/env'")
                os.system(
                    f"ssh {rpi} 'echo \"{env_contents}\" > /home/pi/wcl/{program}/env/.env'"
                )
            else:
                print(f"   No keywords found for {program}")

    print("Finished writing environment files.")

if __name__ == "__main__":
    main()
