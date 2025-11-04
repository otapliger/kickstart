"""
Type definitions for kickstart.

This module contains all custom type definitions used throughout the application.
"""

from typing import TypedDict
from enum import Enum
from dataclasses import dataclass


class MirrorData(TypedDict):
  """Represents a mirror with its URL, region, and location."""

  url: str
  region: str
  location: str


class DefaultsConfig(TypedDict):
  """Configuration defaults for a distribution."""

  repository: str
  timezone: str
  locale: str
  keymap: str
  libc: str
  ntp: list[str]


class GPUVendor(Enum):
  """Enumeration of GPU vendors."""

  INTEL = "intel"
  AMD = "amd"
  NVIDIA = "nvidia"
  UNKNOWN = "unknown"


@dataclass
class ContextConfig:
  """Typed configuration object with all command line arguments."""

  dry: bool
  libc: str
  repository: str | None
  timezone: str
  keymap: str
  locale: str
  hostname: str | None = None
  profile: str | None = None
