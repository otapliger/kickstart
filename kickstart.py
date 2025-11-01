#!/usr/bin/env python3

import argparse
import os
import sys
from pathlib import Path
from typing import override
from src.ansi_codes import red, reset, yellow, bold
from src.ascii_art import print_logo
from src.steps import install
from src.utils import error, info, load_defaults, get_distro_info
from src.context import InstallerContext, Config
from src.profiles import ProfileLoader
from src.validations import validate_cli_arguments
from textwrap import dedent


DEFAULTS = load_defaults()


class IndentedHelpFormatter(argparse.RawDescriptionHelpFormatter):
  def __init__(self, prog: str, **kwargs) -> None:
    super().__init__(prog, max_help_position=30, width=80, **kwargs)

  @override
  def _format_action_invocation(self, action: argparse.Action) -> str:
    options = action.option_strings
    if not options:
      return super()._format_action_invocation(action)
    parts: list[str] = []
    if len(options) == 1:
      parts.append(f"{'':4}{options[0]}")
    else:
      parts.append(f"{', '.join(options)}")
    if action.nargs != 0:
      default_metavar = self._get_default_metavar_for_optional(action)
      parts[-1] += f" {self._format_args(action, default_metavar)}"
    return parts[-1]


def _check_system_requirements() -> None:
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


def _create_argument_parser() -> argparse.ArgumentParser:
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
        %(prog)s --dry                                      # Preview installation steps
        %(prog)s --libc musl --keymap colemak               # Custom configuration
        %(prog)s -r https://mirrors.example.com/void        # Different repository
        %(prog)s --hostname voidlinux                       # Set custom hostname
        %(prog)s --profile ./profiles/minimal.json          # Use local profile

      For more information, visit: https://github.com/otapliger/kickstart
    """),
  )

  _ = parser.add_argument(
    "-d",
    "--dry",
    action="store_true",
    help="preview installation steps without executing commands or writing files",
    dest="dry",
  )
  _ = parser.add_argument(
    "-p",
    "--profile",
    metavar="SOURCE",
    type=str,
    help="load installation profile from local file path or HTTP URL",
    dest="profile",
  )

  _ = parser.add_argument(
    "--libc",
    metavar="LIBC",
    type=str,
    default=DEFAULTS["libc"],
    help="C library implementation (glibc or musl) [default: %(default)s]",
    dest="libc",
  )
  _ = parser.add_argument(
    "-r",
    "--repository",
    metavar="URL",
    type=str,
    default=DEFAULTS["repository"],
    help="override interactive mirror selection with specific repository URL [default: %(default)s]",
    dest="repository",
  )
  _ = parser.add_argument(
    "-t",
    "--timezone",
    metavar="TIMEZONE",
    type=str,
    default=DEFAULTS["timezone"],
    help="system timezone in Region/City format [default: %(default)s]",
    dest="timezone",
  )
  _ = parser.add_argument(
    "-k",
    "--keymap",
    metavar="KEYMAP",
    type=str,
    default=DEFAULTS["keymap"],
    help="keyboard layout for the system [default: %(default)s]",
    dest="keymap",
  )
  _ = parser.add_argument(
    "--locale",
    metavar="LOCALE",
    type=str,
    default=DEFAULTS["locale"],
    help="system locale (e.g., en_US, en_US.UTF-8, C, POSIX) [default: %(default)s]",
    dest="locale",
  )
  _ = parser.add_argument(
    "--hostname",
    metavar="HOSTNAME",
    type=str,
    help="system hostname",
    dest="hostname",
  )
  _ = parser.add_argument("--version", action="version", version="void.kickstart 0.1.0")

  return parser


def _run_installation(ctx: InstallerContext) -> None:
  """Run the installation process with proper error handling."""
  total_steps = len(install)

  for i, step in enumerate(install, 1):
    step_name = step.__name__.replace("step_", "").replace("_", " ").title()
    # Remove leading numbers and spaces to avoid duplication with progress counter
    step_name = step_name.lstrip("0123456789 ")

    if ctx.dry:
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
      if ctx.dry:
        error("This error occurred during dry run - actual installation might fail.")
      sys.exit(1)


def main() -> None:
  """Main entry point for the installer."""
  parser = _create_argument_parser()
  args = parser.parse_args()
  config = Config.from_namespace(args)

  distro_name, distro_id = get_distro_info(dry_run=config.dry)
  print_logo(distro_id)

  if config.dry:
    print(f"{yellow}{bold}DRY RUN MODE{reset} - No actual changes will be made to your system")

  errors = validate_cli_arguments(
    repository=config.repository,
    timezone=config.timezone,
    locale=config.locale,
    libc=config.libc,
    hostname=config.hostname,
    profile=config.profile,
  )

  if errors:
    error("Invalid arguments provided:")
    for err in errors:
      print(f"  • {err}")
    print(f"\n{yellow}Use --help for valid options{reset}")
    sys.exit(1)

  print()

  if not config.dry:
    _check_system_requirements()
  else:
    info("Skipping root and system checks in dry run mode")

  ctx = InstallerContext(config)
  ctx.distro_name = distro_name
  ctx.distro_id = distro_id

  if config.profile:
    try:
      ctx.profile = ProfileLoader.load(config.profile)

      # Apply profile configuration overrides to base config
      # (only if not explicitly set via CLI)
      if ctx.profile.config.libc and ctx.config.libc == DEFAULTS["libc"]:
        ctx.config.libc = ctx.profile.config.libc
      if ctx.profile.config.timezone and ctx.config.timezone == DEFAULTS["timezone"]:
        ctx.config.timezone = ctx.profile.config.timezone
      if ctx.profile.config.keymap and ctx.config.keymap == DEFAULTS["keymap"]:
        ctx.config.keymap = ctx.profile.config.keymap
      if ctx.profile.config.locale and ctx.config.locale == DEFAULTS["locale"]:
        ctx.config.locale = ctx.profile.config.locale
      if ctx.profile.config.repository and ctx.config.repository == DEFAULTS["repository"]:
        ctx.config.repository = ctx.profile.config.repository

    except Exception as e:
      error(f"Failed to load profile: {e}")
      sys.exit(1)

  try:
    print()
    _run_installation(ctx)

    if config.dry:
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
