"""Distro adapter registry"""

import sys
from importlib import import_module
from typing import cast

from rich.console import Console

from src.distros.protocol import DistroProtocol

console = Console()

__all__ = ["get_distro", "get_supported_distros", "DistroProtocol"]


def get_distro(distro_id: str, dry_mode: bool = False) -> DistroProtocol:
  """
  Load and return the distro module for the given distro_id.

  Each distro module must implement the standard function interface.
  In dry mode, falls back to linux module if distro not found.
  """
  try:
    module = import_module(f"src.distros.{distro_id}")
    # Double cast needed: ModuleType -> object -> DistroProtocol
    # Type checker can't verify ModuleType implements Protocol at import time
    module_as_object = cast(object, module)
    return cast(DistroProtocol, module_as_object)

  except ModuleNotFoundError:
    if dry_mode:
      module = import_module("src.distros.linux")
      module_as_object = cast(object, module)
      return cast(DistroProtocol, module_as_object)

    else:
      console.print(f"\n[prompt.invalid]Unsupported distribution: {distro_id}[/]")
      console.print(f"\n[prompt.invalid]No module found at src/distros/{distro_id}.py[/]")
      sys.exit(1)


def get_supported_distros() -> list[str]:
  """Return list of supported distro IDs"""
  return ["void", "arch"]
