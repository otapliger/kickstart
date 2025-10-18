#!/usr/bin/env python3

import argparse
import os
import re
import sys
import urllib.parse
from pathlib import Path


from src.ansi_codes import green, red, reset, yellow, bold
from src.ascii_art import void
from src.steps import install
from src.utils import error, info, InstallerContext
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


def validate_url(url: str) -> bool:
  """Validate that a URL is properly formatted."""
  if not url or not isinstance(url, str):
    return False

  result = urllib.parse.urlparse(url)
  return bool(result.scheme and result.netloc)


def validate_timezone(timezone: str) -> bool:
  """Validate timezone against common timezone patterns."""
  if "/" not in timezone:
    return False
  parts = timezone.split("/")
  if len(parts) != 2:
    return False
  region, city = parts
  if not region.replace("_", "").isalpha() or not city.replace("_", "").isalpha():
    return False
  return True


def validate_locale(locale: str) -> bool:
  """Validate locale format - supports various glibc locale formats."""
  if not locale or not isinstance(locale, str):
    return False

  # Allow C/POSIX locales
  if locale in ("C", "POSIX"):
    return True

  # Basic pattern: language[_territory][.encoding][@modifier]
  # Examples: en, en_US, en_US.UTF-8, en_US@euro, de_DE.ISO-8859-1@euro
  pattern = r"^[a-z]{2,3}(_[A-Z]{2})?(\.[A-Za-z0-9_-]+)?(@[A-Za-z0-9_-]+)?$"
  return bool(re.match(pattern, locale))


def validate_libc(libc: str) -> bool:
  """Validate C library implementation."""
  valid_libcs = {"glibc", "musl"}
  return libc.lower() in valid_libcs


def check_system_requirements() -> None:
  """Check if the system meets installation requirements."""
  if os.geteuid() != 0:
    error("Root privileges are required. Please re-run the script as root.")
    sys.exit(2)

  # Check if /dev exists (basic sanity check)
  if not Path("/dev").exists():
    error("System appears to be in an invalid state - /dev directory not found.")
    sys.exit(3)

  # Check if we're in a live environment or chroot
  if not Path("/proc/mounts").exists():
    error("System appears to be in an invalid state - /proc not mounted.")
    sys.exit(3)


def validate_arguments(args: argparse.Namespace) -> None:
  """Validate all command line arguments."""
  errors = []

  if not validate_url(args.repository):
    errors.append(f"Invalid repository URL: {args.repository}")

  if not validate_timezone(args.timezone):
    errors.append(f"Invalid timezone: {args.timezone} (expected format: Region/City)")

  if not validate_locale(args.locale):
    errors.append(f"Invalid locale: {args.locale} (expected format: language[_COUNTRY][.encoding][@modifier])")

  if not validate_libc(args.libc):
    errors.append(f"Invalid libc: {args.libc} (must be 'glibc' or 'musl')")

  if errors:
    error("Invalid arguments provided:")
    for err in errors:
      print(f"  • {err}")
    print(f"\n{yellow}Use --help for valid options{reset}")
    sys.exit(1)


def create_argument_parser() -> argparse.ArgumentParser:
  """Create and configure the argument parser."""
  parser = argparse.ArgumentParser(
    formatter_class=IndentedHelpFormatter,
    description=dedent("""
      A user-friendly, automated installer for Void Linux,
      designed to simplify and streamline the installation process.

      This installer creates a minimal base system - a clean kickstart
      from which you can build up your environment without bloat.
      It sets up a fully encrypted Void Linux system with BTRFS
      subvolumes and modern boot configuration.
    """),
    epilog=dedent("""
      Examples:
        %(prog)s --dry                          # Preview installation steps
        %(prog)s --libc musl --keymap colemak   # Custom configuration
        %(prog)s --timezone Asia/Bangkok        # Different timezone

      For more information, visit: https://github.com/otapliger/kickstart
    """),
  )

  parser.add_argument(
    "-d",
    "--dry",
    action="store_true",
    help="preview installation steps without executing commands or writing files",
    dest="dry",
  )
  parser.add_argument(
    "--libc",
    metavar="LIBC",
    type=str,
    default="glibc",
    help="C library implementation (glibc or musl) [default: %(default)s]",
    dest="libc",
  )
  parser.add_argument(
    "--repository",
    metavar="URL",
    type=str,
    default="https://repo-fi.voidlinux.org/current",
    help="repository URL for package installation [default: %(default)s]",
    dest="repository",
  )
  parser.add_argument(
    "--timezone",
    metavar="TIMEZONE",
    type=str,
    default="Europe/Helsinki",
    help="system timezone in Region/City format [default: %(default)s]",
    dest="timezone",
  )
  parser.add_argument(
    "--keymap",
    metavar="KEYMAP",
    type=str,
    default="us",
    help="keyboard layout for the system [default: %(default)s]",
    dest="keymap",
  )
  parser.add_argument(
    "--locale",
    metavar="LOCALE",
    type=str,
    default="en_GB.UTF-8",
    help="system locale (e.g., en_US, en_US.UTF-8, C, POSIX) [default: %(default)s]",
    dest="locale",
  )
  parser.add_argument("--version", action="version", version="void.kickstart 0.1.0")

  return parser


def run_installation(ctx: InstallerContext) -> None:
  """Run the installation process with proper error handling."""
  total_steps = len(install)

  for i, step in enumerate(install, 1):
    step_name = step.__name__.replace("step_", "").replace("_", " ").title()
    # Remove leading numbers and spaces to avoid duplication with progress counter
    step_name = step_name.lstrip("0123456789 ")

    if ctx.args.dry:
      info(f"[{i}/{total_steps}] {step_name}")
    else:
      info(f"[{i}/{total_steps}] {step_name}")

    try:
      step(ctx)
    except KeyboardInterrupt:
      print()
      print(f"{red}Installation interrupted by user. Exiting...{reset}")
      sys.exit(130)  # Standard exit code for SIGINT
    except FileNotFoundError as e:
      error(f"Required file or directory not found: {e}")
      error("This might indicate a system configuration issue.")
      sys.exit(4)
    except PermissionError as e:
      error(f"Permission denied: {e}")
      error("Make sure you're running as root and have proper permissions.")
      sys.exit(5)
    except Exception as e:
      error(f"Step '{step_name}' failed with error: {e}")
      error("Installation cannot continue.")
      if ctx.args.dry:
        error("This error occurred during dry run - actual installation might fail.")
      sys.exit(1)


def main() -> None:
  """Main entry point for the installer."""
  parser = create_argument_parser()
  args = parser.parse_args()

  # Print banner
  print(void)
  print(f"{green}Welcome to void.kickstart, a Void Linux installer.{reset}")

  if args.dry:
    print(f"{yellow}{bold}DRY RUN MODE{reset} - No actual changes will be made to your system")

  print()

  # Validate arguments
  validate_arguments(args)

  # Check system requirements (skip some checks in dry run mode)
  if not args.dry:
    check_system_requirements()
  else:
    info("Skipping root and system checks in dry run mode")

  # Create installer context
  ctx = InstallerContext(args)

  # Run installation
  try:
    run_installation(ctx)

    if args.dry:
      print()
      info("Dry run completed successfully!")
      info("Run without --dry flag to perform actual installation.")
    else:
      print()
      info("Installation completed successfully!")
      info("You can now reboot your system to start using Void Linux.")

  except Exception as e:
    error(f"Unexpected error during installation: {e}")
    sys.exit(1)


if __name__ == "__main__":
  try:
    main()
  except KeyboardInterrupt:
    print()
    print(f"{red}Installation interrupted. Exiting...{reset}")
    sys.exit(130)
  except Exception as e:
    error(f"Fatal error: {e}")
    sys.exit(1)
