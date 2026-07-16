#!/usr/bin/env python3
"""
pSTRminer – unified entry point
================================
  • With no arguments → launch GUI
  • With arguments    → CLI mode (pstrminer config ... / pstrminer poly ...)
"""

import sys


def main():
    # If any CLI sub-command is given, route to CLI
    if len(sys.argv) > 1:
        from pstrminer.cli import main as cli_main
        cli_main()
    else:
        # Check that tkinter is available before importing GUI
        try:
            import tkinter  # noqa: F401
        except ImportError:
            print(
                "Error: Tkinter is not available on this system.\n"
                "Run pSTRminer with CLI arguments instead:\n"
                "  pstrminer config --help\n"
                "  pstrminer poly   --help",
                file=sys.stderr,
            )
            sys.exit(1)
        from pstrminer.gui import main as gui_main
        gui_main()


if __name__ == "__main__":
    main()
