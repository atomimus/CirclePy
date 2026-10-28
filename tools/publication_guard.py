"""Fail closed until an exact-artifact trusted publication pipeline is configured."""

import sys


def main():
    print("Publication is disabled: the trusted publishing task must first configure "
          "protected PyPI/TestPyPI environments, release authorization, exact-SHA "
          "required checks and prepublication validation of the retained artifact bytes.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
