"""
Profile management system for kickstart.

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
from typing import cast
from src.ansi_codes import green, yellow, reset
from src.utils import error, info
from src.validations import validate_profile_json, is_string_list


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

  additional: list[str] = field(default_factory=list)
  exclude: list[str] = field(default_factory=list)


@dataclass
class InstallationProfile:
  """Installation profile definition."""

  name: str
  description: str
  distro: str
  version: str = "1.0"
  config: ProfileConfig = field(default_factory=ProfileConfig)
  packages: PackageSelection = field(default_factory=PackageSelection)
  post_install_commands: list[str] = field(default_factory=list)
  hostname: str | None = None

  @classmethod
  def from_dict(cls, data: dict[str, object]) -> InstallationProfile:
    """Create profile from dictionary (loaded JSON)."""
    required_fields = ["name", "description", "distro"]

    if missing := [k for k in required_fields if k not in data]:
      raise ValueError(f"Profile must have {', '.join(repr(k) for k in missing)} field(s)")

    # Extract and validate types
    name, description, distro = data["name"], data["description"], data["distro"]

    if not all(isinstance(v, str) for v in [name, description, distro]):
      invalid = [
        k for k, v in [("name", name), ("description", description), ("distro", distro)] if not isinstance(v, str)
      ]
      raise ValueError(f"Profile fields {', '.join(repr(k) for k in invalid)} must be strings")

    # Cast to str after validation
    name, description, distro = str(name), str(description), str(distro)

    config_data = data.get("config", {})
    config_data = config_data if isinstance(config_data, dict) else {}
    config_fields = ["libc", "timezone", "keymap", "locale", "repository"]
    config_values = {k: config_data.get(k) if isinstance(config_data.get(k), str) else None for k in config_fields}

    config = ProfileConfig(**config_values)

    # Create package selection
    packages_data = data.get("packages", {})
    if not isinstance(packages_data, dict):
      packages_data = {}

    additional_packages = packages_data.get("additional", [])
    exclude_packages = packages_data.get("exclude", [])

    packages = PackageSelection(
      additional=cast(list[str], additional_packages) if is_string_list(additional_packages) else [],
      exclude=cast(list[str], exclude_packages) if is_string_list(exclude_packages) else [],
    )

    version = str(version_raw) if (version_raw := data.get("version", "1.0")) is not None else "1.0"
    hostname = hostname_raw if isinstance(hostname_raw := data.get("hostname"), str) else None
    post_install_commands = (
      cast(list[str], commands_raw) if is_string_list(commands_raw := data.get("post_install_commands", [])) else []
    )

    return cls(
      name=name,
      description=description,
      version=version,
      distro=distro,
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
      "distro": self.distro,
      "version": self.version,
    }

    # Build config dict using comprehension, filtering out None values
    config_dict = {
      k: v
      for k, v in {
        "libc": self.config.libc,
        "timezone": self.config.timezone,
        "keymap": self.config.keymap,
        "locale": self.config.locale,
        "repository": self.config.repository,
      }.items()
      if v is not None
    }

    # Build packages dict using comprehension, filtering out empties
    packages_dict = {
      k: v
      for k, v in {
        "additional": self.packages.additional,
        "exclude": self.packages.exclude,
      }.items()
      if v
    }

    # Build optional fields dict, filtering out empties
    optional_fields = {
      k: v
      for k, v in {
        "config": config_dict,
        "packages": packages_dict,
        "hostname": self.hostname,
        "post_install_commands": self.post_install_commands,
      }.items()
      if v
    }

    return {**result, **optional_fields}


class ProfileLoader:
  """Handles loading profiles from local files or HTTP URLs."""

  @staticmethod
  def _load_from_url(url: str) -> dict[str, object]:
    """Load JSON data from HTTP URL."""
    try:
      req = urllib.request.Request(
        url,
        headers={
          "User-Agent": "kickstart/0.1.0",
          "Accept": "application/json",
        },
      )

      with urllib.request.urlopen(req, timeout=10) as response:
        status_code = getattr(response, "status", getattr(response, "code", 200))

        if status_code != 200:
          reason = getattr(response, "reason", "Unknown error")
          raise ValueError(f"HTTP {status_code}: {reason}")

        content_type = response.headers.get("Content-Type", "")
        if content_type and "application/json" not in content_type and "text/json" not in content_type:
          print(f"{yellow}Warning: Server returned Content-Type '{content_type}', expected JSON{reset}")

        parsed_data = json.loads(response.read().decode("utf-8"))
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

      validation_issues = validate_profile_json(data)
      if validation_issues:
        error(f"Profile validation failed for '{source}':")
        for issue in validation_issues:
          print(f" • {issue}")

        raise ValueError(f"Profile contains {len(validation_issues)} validation error(s)")

      profile = InstallationProfile.from_dict(data)
      return profile

    except Exception as e:
      error(f"Failed to load profile from '{source}': {e}")
      raise
