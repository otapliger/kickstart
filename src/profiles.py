"""
Profile management system for void.kickstart.

Supports loading installation profiles from local files or HTTP URLs.
Profiles define predefined configurations that can override defaults
and specify package selections, custom settings, and installation behavior.
"""

from __future__ import annotations
import urllib.request
import urllib.error
import json
from dataclasses import dataclass, field
from pathlib import Path
from src.ansi_codes import green, yellow, reset
from src.utils import error, info
from src.validations import validate_profile_json


@dataclass
class ProfileConfig:
  """Configuration overrides defined in a profile."""

  libc: str | None = None
  timezone: str | None = None
  keymap: str | None = None
  locale: str | None = None
  repository: str | None = None


@dataclass
class PackageSelection:
  """Package selection configuration."""

  additional: list[str] = field(default_factory=list)  # Additional packages
  exclude: list[str] = field(default_factory=list)  # Packages to exclude


@dataclass
class InstallationProfile:
  """Installation profile definition."""

  name: str
  description: str
  version: str = "1.0"
  config: ProfileConfig = field(default_factory=ProfileConfig)
  packages: PackageSelection = field(default_factory=PackageSelection)
  post_install_commands: list[str] = field(default_factory=list)
  hostname: str | None = None

  @classmethod
  def from_dict(cls, data: dict[str, object]) -> InstallationProfile:
    """Create profile from dictionary (loaded JSON)."""
    # Validate required fields
    if "name" not in data:
      raise ValueError("Profile must have a 'name' field")
    if "description" not in data:
      raise ValueError("Profile must have a 'description' field")

    name = data["name"]
    description = data["description"]

    if not isinstance(name, str):
      raise ValueError("Profile 'name' must be a string")
    if not isinstance(description, str):
      raise ValueError("Profile 'description' must be a string")

    # Create config overrides
    config_data = data.get("config", {})
    if not isinstance(config_data, dict):
      config_data = {}

    config = ProfileConfig(
      libc=config_data.get("libc") if isinstance(config_data.get("libc"), str) else None,
      timezone=config_data.get("timezone") if isinstance(config_data.get("timezone"), str) else None,
      keymap=config_data.get("keymap") if isinstance(config_data.get("keymap"), str) else None,
      locale=config_data.get("locale") if isinstance(config_data.get("locale"), str) else None,
      repository=config_data.get("repository") if isinstance(config_data.get("repository"), str) else None,
    )

    # Create package selection
    packages_data = data.get("packages", {})
    if not isinstance(packages_data, dict):
      packages_data = {}

    additional_packages = packages_data.get("additional", [])
    exclude_packages = packages_data.get("exclude", [])

    packages = PackageSelection(
      additional=additional_packages
      if isinstance(additional_packages, list) and all(isinstance(p, str) for p in additional_packages)
      else [],
      exclude=exclude_packages
      if isinstance(exclude_packages, list) and all(isinstance(p, str) for p in exclude_packages)
      else [],
    )

    # Get version
    version_raw = data.get("version", "1.0")
    version = str(version_raw) if version_raw is not None else "1.0"

    # Get hostname
    hostname_raw = data.get("hostname")
    hostname = hostname_raw if isinstance(hostname_raw, str) else None

    # Get post-install commands
    commands_raw = data.get("post_install_commands", [])
    post_install_commands = (
      commands_raw if isinstance(commands_raw, list) and all(isinstance(c, str) for c in commands_raw) else []
    )

    return cls(
      name=name,
      description=description,
      version=version,
      config=config,
      packages=packages,
      hostname=hostname,
      post_install_commands=post_install_commands,
    )

  def to_dict(self) -> dict[str, object]:
    """Convert profile to dictionary for JSON serialization."""
    result: dict[str, object] = {
      "name": self.name,
      "description": self.description,
      "version": self.version,
    }

    # Add config if any values are set
    config_dict: dict[str, str] = {}
    if self.config.libc is not None:
      config_dict["libc"] = self.config.libc
    if self.config.timezone is not None:
      config_dict["timezone"] = self.config.timezone
    if self.config.keymap is not None:
      config_dict["keymap"] = self.config.keymap
    if self.config.locale is not None:
      config_dict["locale"] = self.config.locale
    if self.config.repository is not None:
      config_dict["repository"] = self.config.repository

    if config_dict:
      result["config"] = config_dict

    # Add packages if any are specified
    packages_dict: dict[str, list[str]] = {}
    if self.packages.additional:
      packages_dict["additional"] = self.packages.additional
    if self.packages.exclude:
      packages_dict["exclude"] = self.packages.exclude

    if packages_dict:
      result["packages"] = packages_dict

    # Add optional fields
    if self.hostname is not None:
      result["hostname"] = self.hostname
    if self.post_install_commands:
      result["post_install_commands"] = self.post_install_commands

    return result


class ProfileLoader:
  """Handles loading profiles from local files or HTTP URLs."""

  @staticmethod
  def _load_from_url(url: str) -> dict[str, object]:
    """Load JSON data from HTTP URL."""
    try:
      info(f"Loading profile from {url}")

      # Create request with reasonable timeout and user agent
      req = urllib.request.Request(
        url,
        headers={
          "User-Agent": "void.kickstart/0.1.0",
          "Accept": "application/json",
        },
      )

      with urllib.request.urlopen(req, timeout=10) as response:
        # Check response status - handle different response types
        if hasattr(response, "status"):
          status_code = response.status
        elif hasattr(response, "code"):
          status_code = response.code
        else:
          status_code = 200

        if status_code != 200:
          if hasattr(response, "reason"):
            reason = response.reason
          else:
            reason = "Unknown error"
          raise ValueError(f"HTTP {status_code}: {reason}")

        # Check content type
        content_type = ""
        if hasattr(response, "headers") and hasattr(response.headers, "get"):
          content_type = response.headers.get("Content-Type", "")

        if content_type and "application/json" not in content_type and "text/json" not in content_type:
          print(f"{yellow}Warning: Server returned Content-Type '{content_type}', expected JSON{reset}")

        # Read and decode response
        data_bytes = response.read()
        data_str = data_bytes.decode("utf-8")
        parsed_data = json.loads(data_str)

        if not isinstance(parsed_data, dict):
          raise ValueError("Profile JSON must be an object")

        return parsed_data

    except urllib.error.URLError as e:
      raise ValueError(f"Failed to load profile from URL: {e}") from e
    except json.JSONDecodeError as e:
      raise ValueError(f"Invalid JSON in profile: {e}") from e

  @staticmethod
  def _load_from_file(file_path: str | Path) -> dict[str, object]:
    """Load JSON data from local file."""
    try:
      path = Path(file_path)
      if not path.exists():
        raise FileNotFoundError(f"Profile file not found: {path}")

      info(f"Loading profile from {path}")

      with open(path, "r", encoding="utf-8") as f:
        parsed_data = json.load(f)

        if not isinstance(parsed_data, dict):
          raise ValueError("Profile JSON must be an object")

        return parsed_data

    except json.JSONDecodeError as e:
      raise ValueError(f"Invalid JSON in profile file: {e}") from e
    except OSError as e:
      raise ValueError(f"Failed to read profile file: {e}") from e

  @classmethod
  def load(cls, source: str) -> InstallationProfile:
    """
    Load profile from source (URL or file path).

    Args:
        source: HTTP URL starting with http:// or https://, or local file path

    Returns:
        InstallationProfile object

    Raises:
        ValueError: If profile cannot be loaded or is invalid
    """
    try:
      if source.startswith(("http://", "https://")):
        data = cls._load_from_url(source)
      else:
        data = cls._load_from_file(source)

      # Perform automatic validation - only show output if validation fails
      validation_issues = validate_profile_json(data)
      if validation_issues:
        error(f"Profile validation failed for '{source}':")
        for issue in validation_issues:
          print(f"  • {issue}")
        raise ValueError(f"Profile contains {len(validation_issues)} validation error(s)")

      profile = InstallationProfile.from_dict(data)
      info(f"Successfully loaded profile: {green}{profile.name}{reset}")

      return profile

    except Exception as e:
      error(f"Failed to load profile from '{source}': {e}")
      raise


def create_example_profile() -> dict[str, object]:
  """Create an example profile for documentation/testing."""
  return {
    "name": "Minimal System",
    "description": "Bare minimum Void Linux installation with only essential packages",
    "version": "1.0",
    "config": {"libc": "glibc", "timezone": "Europe/London", "keymap": "uk", "locale": "en_GB.UTF-8"},
    "packages": {
      "additional": ["neovim", "lua"],
      "exclude": ["helix"],
    },
    "hostname": "void",
    "post_install_commands": [],
  }
