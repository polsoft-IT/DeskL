"""DeskL — punkt wejścia aplikacji (cienki launcher)."""

import os
import sys


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    if root not in sys.path:
        sys.path.insert(0, root)
    from deskl.app import main as run
    return run()


if __name__ == "__main__":
    sys.exit(main())
