"""
Type definitions for kickstart.

This module contains all custom type definitions used throughout the application.
"""

from typing import TypedDict


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
