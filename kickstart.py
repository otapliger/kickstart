#!/usr/bin/env python3

import argparse
import os
import sys
from argparse import Namespace
from textwrap import dedent
from typing import override

from rich.console import Console

from src.ascii import print_logo
from src.context import ContextConfig, InstallerContext
from src.profiles import ProfileLoader
from src.steps import get_install_steps
from src.tui import TUI
from src.utils import DefaultsConfig, format_step_name, get_distro_info, load_defaults
from src.validations import validate_cli_arguments

console = Console()


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
    console.print("\n[prompt.invalid]Root privileges are required. Please re-run the script as root.[/]")
    sys.exit(2)

  try:
    with open("/proc/mounts", "r") as f:
      if any(line.split()[1].startswith("/mnt") for line in f if line.strip() and len(line.split()) > 1):
        console.print("\n[prompt.invalid]/mnt is currently mounted or has mounted subdirectories.[/]")
        console.print("Please unmount before running the installer.")
        sys.exit(2)
  except (FileNotFoundError, IOError):
    pass


def _create_argument_parser(defaults: DefaultsConfig) -> argparse.ArgumentParser:
  """Create and configure the argument parser."""
  parser = argparse.ArgumentParser(
    formatter_class=IndentedHelpFormatter,
    description=dedent("""
      A user-friendly, automated installer for supported Linux distros,
      designed to simplify and streamline the installation process.

      This installer creates a minimal base system - a clean kickstart
      from which you can build up your environment without bloat.
      It sets up a fully encrypted Linux system with BTRFS
      subvolumes and modern boot configuration.
    """),
    epilog=dedent("""
      Examples:
        %(prog)s --dry                              # Preview installation steps
        %(prog)s --keymap fi --locale fi_FI.UTF-8   # Custom keymap and locale
        %(prog)s --timezone Europe/Lisbon           # Custom timezone
        %(prog)s --profile niri                     # Use embedded profile by name

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
    metavar="PROFILE",
    type=str,
    help="load installation profile by name, file path, or HTTP URL",
    dest="profile",
  )

  _ = parser.add_argument(
    "--libc",
    metavar="LIBC",
    type=str,
    default=defaults["libc"],
    help="C library implementation (glibc or musl) [default: %(default)s]",
    dest="libc",
  )

  _ = parser.add_argument(
    "-r",
    "--repository",
    metavar="URL",
    type=str,
    default=None,
    help=f"override interactive mirror selection with specific repository URL [default: {defaults['repository']}]",
    dest="repository",
  )

  _ = parser.add_argument(
    "-t",
    "--timezone",
    metavar="TIMEZONE",
    type=str,
    default=defaults["timezone"],
    help="system timezone in Region/City format [default: %(default)s]",
    dest="timezone",
  )

  _ = parser.add_argument(
    "-k",
    "--keymap",
    metavar="KEYMAP",
    type=str,
    default=defaults["keymap"],
    help="keyboard layout for the system [default: %(default)s]",
    dest="keymap",
  )

  _ = parser.add_argument(
    "--locale",
    metavar="LOCALE",
    type=str,
    default=defaults["locale"],
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

  _ = parser.add_argument("--version", action="version", version="kickstart 0.1.0")

  return parser


def _create_context_config(args: Namespace) -> ContextConfig:
  """Create a typed ContextConfig from an argparse Namespace."""
  return ContextConfig(
    dry=bool(getattr(args, "dry", False)),
    libc=str(getattr(args, "libc", "glibc")),
    repository=getattr(args, "repository", None),
    timezone=str(getattr(args, "timezone", "UTC")),
    keymap=str(getattr(args, "keymap", "us")),
    locale=str(getattr(args, "locale", "C")),
    hostname=getattr(args, "hostname", None),
    profile=getattr(args, "profile", None),
  )


def _run_installation(ctx: InstallerContext, ui: TUI, warnings: list[str]) -> None:
  """Run the installation process with proper error handling."""
  steps = get_install_steps(ctx)
  total_steps = len(steps) - 1  # Exclude step 0 from count

  for i, step in enumerate(steps):
    step_name = format_step_name(step.__name__)

    # Status line (exclude step 0 from status bar display)
    if i > 0:
      filled = "▓" * i
      empty = "░" * (total_steps - i)
      progress_bar = f"[{filled}{empty}]"
      ui.update_status(f"{progress_bar} {step_name} · Step {i}/{total_steps}", step_name)

    try:
      step(ctx, warnings)

    except KeyboardInterrupt:
      ui.cleanup()
      console.print("\n\n[prompt.invalid]Installation interrupted by user. Exiting...[/]")
      sys.exit(130)

    except Exception as e:
      ui.cleanup()
      console.print(f"\n[prompt.invalid]Step '{step_name}' failed with error: {e}[/]")
      console.print("\n[prompt.invalid]Installation cannot continue.[/]")
      if ctx.dry:
        console.print("\n[prompt.invalid]This error occurred during dry run - actual installation might fail.[/]")
      sys.exit(1)

  # Clear status line when installation completes
  ui.cleanup()


def main() -> None:
  """Main entry point for the installer."""
  # Detect distro - get_distro_info returns defaults if file missing
  distro_name, distro_id = get_distro_info()

  # Collect warnings during dry mode to display at the end
  warnings: list[str] = []
  defaults = load_defaults(distro_id)
  parser = _create_argument_parser(defaults)
  config = _create_context_config(parser.parse_args())

  # In dry mode with a profile, use the profile's distro
  profile = None
  if config.dry and config.profile:
    try:
      profile = ProfileLoader.load(config.profile, distro_id)
      distro_id = profile.distro
      distro_name = profile.distro.capitalize()
      defaults = load_defaults(distro_id)
    except Exception as e:
      console.print(f"\n[prompt.invalid]Failed to load profile: {e}[/]")
      sys.exit(1)

  errors = validate_cli_arguments(
    repository=config.repository,
    timezone=config.timezone,
    locale=config.locale,
    libc=config.libc,
    hostname=config.hostname,
    profile=config.profile,
    distro_id=distro_id,
  )

  if errors:
    console.print("\n[prompt.invalid]Invalid arguments provided:[/]")
    console.print("\n".join(f" • {err}" for err in errors))
    console.print("\n[yellow]Use --help for valid options[/]")
    sys.exit(1)

  if not config.dry:
    _check_system_requirements()

  ctx = InstallerContext(config)
  ctx.distro_name = distro_name
  ctx.distro_id = distro_id

  if config.profile:
    if profile:
      ctx.profile = profile
    else:
      try:
        ctx.profile = ProfileLoader.load(config.profile, distro_id)

        if ctx.profile.distro != ctx.distro_id:
          msg = f"Profile distro mismatch - profile requires '{ctx.profile.distro}' but system is '{ctx.distro_id}'"
          console.print(f"\n[prompt.invalid]{msg}[/]")
          sys.exit(1)

      except Exception as e:
        console.print(f"\n[prompt.invalid]Failed to load profile: {e}[/]")
        sys.exit(1)

    # Apply profile configuration overrides to base config
    # (only if not explicitly set via CLI)
    config_fields = ["libc", "timezone", "keymap", "locale", "repository"]

    # fmt: off
    for field in (
      f for f in config_fields
      if getattr(ctx.profile.config, f)
      and getattr(ctx.config, f) == defaults[f]
    ):
      setattr(ctx.config, field, getattr(ctx.profile.config, field))
    # fmt: on

  ctx.ui = TUI(dry_mode=config.dry, distro_id=distro_id)

  try:
    # Print logo and dry run banner
    print_logo(ctx.distro_id)
    console.print()
    if config.dry:
      console.print("[bold yellow]DRY RUN MODE[/] - No actual changes will be made to your system")
      console.print()

    _run_installation(ctx, ctx.ui, warnings)

    if config.dry:
      console.print("\n")

      # Display collected warnings
      if warnings:
        console.print("[bold yellow]Warnings encountered during dry run:[/]")
        for warning in warnings:
          console.print(f" • {warning}")
        console.print()

      console.print("[bold green]Dry run completed successfully![/]")
      console.print("[bold green]Run without --dry flag to perform actual installation.[/]")
      console.print()

    else:
      console.print("\n")
      console.print("[bold green]Installation completed successfully![/]")
      console.print("[bold green]You can now reboot your system.[/]")
      console.print()

  except Exception as e:
    console.print(f"\n[prompt.invalid]Unexpected error during installation: {e}[/]")
    sys.exit(1)


if __name__ == "__main__":
  try:
    main()

  except KeyboardInterrupt:
    console.print("\n[prompt.invalid]Installation interrupted. Exiting...[/]")
    sys.exit(130)

  except Exception as e:
    console.print(f"\n[prompt.invalid]Fatal error: {e}[/]")
    sys.exit(1)
