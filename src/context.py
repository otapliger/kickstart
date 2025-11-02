from __future__ import annotations
from src.profiles import InstallationProfile
from src.types import ContextConfig


class InstallerContext:
  """
  Holds the state and configuration for the installation process.

  This context object is passed between installation steps to maintain
  user choices and system state throughout the installation, including
  mirror selection, disk configuration, and user credentials.
  """

  def __init__(self, config: ContextConfig) -> None:
    self.config: ContextConfig = config
    self.profile: InstallationProfile | None = None

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
