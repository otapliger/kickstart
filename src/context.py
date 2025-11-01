from __future__ import annotations
from argparse import Namespace
from dataclasses import dataclass
from typing import Optional
from src.profiles import InstallationProfile


@dataclass
class Config:
  """Typed configuration object with all command line arguments."""

  dry: bool
  libc: str
  repository: str
  timezone: str
  keymap: str
  locale: str
  hostname: Optional[str] = None
  profile: Optional[str] = None

  @classmethod
  def from_namespace(cls, args: Namespace) -> Config:
    """Create a typed Config from an argparse Namespace."""
    return cls(
      dry=bool(getattr(args, "dry", False)),
      libc=str(getattr(args, "libc", "glibc")),
      repository=str(getattr(args, "repository", "")),
      timezone=str(getattr(args, "timezone", "UTC")),
      keymap=str(getattr(args, "keymap", "us")),
      locale=str(getattr(args, "locale", "C")),
      hostname=getattr(args, "hostname", None),
      profile=getattr(args, "profile", None),
    )


class InstallerContext:
  """
  Holds the state and configuration for the Void Linux installation process.

  This context object is passed between installation steps to maintain
  user choices and system state throughout the installation, including
  mirror selection, disk configuration, and user credentials.
  """

  def __init__(self, config: Config) -> None:
    self.config: Config = config
    self.profile: Optional[InstallationProfile] = None

    # Distribution information
    self.distro_name: str = "Linux"
    self.distro_id: str = "linux"

    # User-provided configuration
    self.host: str | None = None
    self.disk: str | None = None
    self.luks_pass: str | None = None
    self.user_name: str | None = None
    self.user_pass: str | None = None
    self.repository: str | None = None

    # System-generated paths
    self.cryptroot: str | None = None
    self.esp: str | None = None
    self.root: str | None = None

  @property
  def dry(self) -> bool:
    """Access dry run flag from config."""
    return self.config.dry
