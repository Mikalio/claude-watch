"""Wristling's commands. Today there is one: python -m wristling setup"""

import sys

from wristling import setup

COMMANDS = {"setup": setup.main}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in COMMANDS:
        print("Usage: python -m wristling setup [--redo STEP]\n\n" + setup.__doc__)
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
