import sys
import subprocess


COMMANDS = {
    "copy-programs": "src/copy-programs.py",
    "write-env-file": "src/write-env-file.py",
    "enable-programs": "src/enable-programs.py",
    "update-programs": "src/update-programs.py",
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print("Usage: uv run main.py <command>")
        print(f"Commands: {', '.join(COMMANDS)}")
        return 1

    result = subprocess.run(["uv", "run", COMMANDS[sys.argv[1]]], check=False)
    return result.returncode

if __name__ == "__main__":
    raise SystemExit(main())
