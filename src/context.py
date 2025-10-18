from typing import Optional
from argparse import Namespace


class InstallerContext:
  """
  Holds the state and configuration for the Void Linux installation process.

  This context object is passed between installation steps to maintain
  user choices and system state throughout the installation.
  """

  def __init__(self, args: Namespace) -> None:
    # Command line arguments
    self.args: Namespace = args

    # User-provided configuration (collected during step 1)
    self.host: Optional[str] = None
    self.disk: Optional[str] = None
    self.luks_pass: Optional[str] = None
    self.user_name: Optional[str] = None
    self.user_pass: Optional[str] = None

    # System-generated paths (set during disk setup)
    self.cryptroot: Optional[str] = None
    self.esp: Optional[str] = None
    self.root: Optional[str] = None
