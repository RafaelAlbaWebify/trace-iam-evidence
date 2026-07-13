import subprocess
import sys
from pathlib import Path


def main() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "src"],
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    Path("mypy-results.txt").write_text(output, encoding="utf-8")
    print(output, end="")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
