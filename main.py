"""StegoHide command-line entry point."""

import sys

from cli.commands import main as cli_main
from cli.menu import main_menu


if __name__ == "__main__":
    # No command supplied -> open interactive menu
    if len(sys.argv) == 1:
        main_menu()

    # Command supplied -> use the existing CLI commands
    else:
        raise SystemExit(cli_main())