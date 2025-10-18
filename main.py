import argparse
import os
import sys

from src.ansi_codes import green, red, reset
from src.ascii_art import void
from src.steps import install
from src.utils import error, InstallerContext
from textwrap import dedent


class IndentedHelpFormatter(argparse.RawDescriptionHelpFormatter):
  def _format_action_invocation(self, action: argparse.Action) -> str:
    options = action.option_strings
    if not options:
      return super()._format_action_invocation(action)
    parts = []
    if len(options) == 1:
      parts.append(f"{'':4}{options[0]}")
    else:
      parts.append(f"{', '.join(options)}")
    if action.nargs != 0:
      parts[-1] += f" {self._format_args(action, self._get_default_metavar_for_optional(action))}"
    return parts[-1]


def main() -> None:
  parser = argparse.ArgumentParser(
    formatter_class=IndentedHelpFormatter,
    description=dedent("""
      A user-friendly, automated installer for Void Linux,
      designed to simplify and streamline the installation process.
    """),
  )
  parser.add_argument("-d", "--dry", action="store_true", help="print commands instead of executing them", dest="dry")
  parser.add_argument(
    "--libc",
    metavar="LIBC",
    type=str,
    default="glibc",
    help="specify the C library implementation to use (e.g., glibc or musl)",
    dest="libc",
  )
  parser.add_argument(
    "--repository",
    metavar="URL",
    type=str,
    default="https://repo-fi.voidlinux.org/current",
    help="repository URL to use for the installation",
    dest="repository",
  )
  parser.add_argument(
    "--timezone",
    metavar="TIMEZONE",
    type=str,
    default="Europe/Helsinki",
    help="specify the system timezone",
    dest="timezone",
  )
  parser.add_argument(
    "--keymap",
    metavar="KEYMAP",
    type=str,
    default="us",
    help="specify the keyboard layout to use",
    dest="keymap",
  )
  parser.add_argument(
    "--locale",
    metavar="LOCALE",
    type=str,
    default="en_GB.UTF-8",
    help="specify the system locale",
    dest="locale",
  )

  args = parser.parse_args()

  print(void)
  print(f"{green}Welcome to void.kickstart, a Void Linux installer.{reset}")

  if os.geteuid() != 0:
    error("Root privileges are required. Please re-run the script as root.")
    sys.exit(1)

  ctx = InstallerContext(args)

  for step in install:
    try:
      step(ctx)
    except Exception as e:
      error(f"Step failed with error: {e}")
      sys.exit(1)


if __name__ == "__main__":
  try:
    main()
  except KeyboardInterrupt:
    print()
    print(f"{red}Installation interrupted. Exiting...{reset}")
    sys.exit(0)
