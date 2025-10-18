from argparse import Namespace


class InstallerContext:
  """
  Holds the state and configuration for the Void Linux installation process.

  This context object is passed between installation steps to maintain
  user choices and system state throughout the installation, including
  mirror selection, disk configuration, and user credentials.
  """

  def __init__(self, args: Namespace) -> None:
    # Command line arguments
    self.args: Namespace = args

    # User-provided configuration (collected during step 1)
    self.host: str | None = None
    self.disk: str | None = None
    self.luks_pass: str | None = None
    self.user_name: str | None = None
    self.user_pass: str | None = None
    self.repository: str | None = None

    # System-generated paths (set during disk setup)
    self.cryptroot: str | None = None
    self.esp: str | None = None
    self.root: str | None = None
