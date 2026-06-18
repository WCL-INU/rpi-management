import sys
import subprocess


COMMANDS = {
    "copy-programs": "src/copy-programs.py",
    "write-env-file": "src/write-env-file.py",
    "enable-programs": "src/enable-programs.py",
    "update-programs": "src/update-programs.py",
    "web": "src/web.py",
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: uv run main.py <command> [args...]")
        print(f"Commands: {', '.join(COMMANDS)}")
        return 1

    try:
        result = subprocess.run(
            ["uv", "run", COMMANDS[sys.argv[1]], *sys.argv[2:]], check=False
        )
    except KeyboardInterrupt:
        return 130
    return result.returncode

if __name__ == "__main__":
    raise SystemExit(main())
