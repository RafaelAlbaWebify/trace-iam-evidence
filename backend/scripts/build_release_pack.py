from argparse import ArgumentParser
from pathlib import Path

from trace_iam.release import build_release_proof


def main() -> None:
    parser = ArgumentParser(description="Build TRACE public-safe release proof")
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=Path("../examples/scenarios"),
        help="Directory containing public-safe scenario JSON files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("../release-proof"),
        help="Directory to replace with generated reports and manifest",
    )
    args = parser.parse_args()
    manifest = build_release_proof(args.scenarios.resolve(), args.output.resolve())
    print(f"Release proof generated: {manifest}")


if __name__ == "__main__":
    main()
