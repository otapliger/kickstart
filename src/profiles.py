"""
Profile management system for kickstart.

Supports loading installation profiles from local files, HTTP URLs, or embedded profiles.
Profiles define predefined configurations that can override defaults
and specify package selections, custom settings, and installation behavior.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from rich.console import Console

from src.registry import get_embedded_profile
from src.validations import validate_profile_json

console = Console()


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
  config: ProfileConfig = field(default_factory=ProfileConfig)
  packages: PackageSelection = field(default_factory=PackageSelection)
  post_install_commands: list[str] = field(default_factory=list)
  hostname: str | None = None

  @classmethod
  def from_dict(cls, data: dict[str, object]) -> InstallationProfile:
    """Create profile from dictionary."""
    name = str(data["name"])
    description = str(data["description"])
    distro = str(data["distro"])

    config_data = data.get("config", {})
    config = (
      ProfileConfig(
        libc=str(config_data.get("libc")) if isinstance(config_data.get("libc"), str) else None,
        timezone=str(config_data.get("timezone")) if isinstance(config_data.get("timezone"), str) else None,
        keymap=str(config_data.get("keymap")) if isinstance(config_data.get("keymap"), str) else None,
        locale=str(config_data.get("locale")) if isinstance(config_data.get("locale"), str) else None,
        repository=str(config_data.get("repository")) if isinstance(config_data.get("repository"), str) else None,
      )
      if isinstance(config_data, dict)
      else ProfileConfig()
    )

    packages_data = data.get("packages", {})
    packages = (
      PackageSelection(
        additional=cast(list[str], packages_data.get("additional", [])),
        exclude=cast(list[str], packages_data.get("exclude", [])),
      )
      if isinstance(packages_data, dict)
      else PackageSelection()
    )

    hostname = str(data["hostname"]) if isinstance(data.get("hostname"), str) else None
    post_install_commands = cast(list[str], data.get("post_install_commands", []))

    return cls(
      name=name,
      description=description,
      distro=distro,
      config=config,
      packages=packages,
      hostname=hostname,
      post_install_commands=post_install_commands,
    )


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
          console.print(f"[yellow]Warning: Server returned Content-Type '{content_type}', expected JSON[/]")

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
  def load(cls, source: str, distro_id: str | None = None) -> InstallationProfile:
    """
    Load profile from source (profile name, file path, or HTTP URL).

    Args:
        source: Profile name (e.g., 'minimal'), HTTP URL, or local file path
        distro_id: Distribution ID for embedded profile lookup (required if source is a name)

    Returns:
        InstallationProfile object

    Raises:
        ValueError: If profile cannot be loaded or is invalid
    """
    try:
      if distro_id and not source.startswith(("http://", "https://", "/", "./")):
        data = get_embedded_profile(distro_id, source)
        if data:
          validation_issues = validate_profile_json(data)
          if validation_issues:
            console.print(f"\n[prompt.invalid]Profile validation failed for '{source}':[/]")
            for issue in validation_issues:
              console.print(f" • {issue}")
            raise ValueError(f"Profile contains {len(validation_issues)} validation error(s)")

          profile = InstallationProfile.from_dict(data)
          return profile

      if source.startswith(("http://", "https://")):
        data = cls._load_from_url(source)
      else:
        data = cls._load_from_file(source)

      validation_issues = validate_profile_json(data)
      if validation_issues:
        console.print(f"\n[prompt.invalid]Profile validation failed for '{source}':[/]")
        for issue in validation_issues:
          console.print(f" • {issue}")

        raise ValueError(f"Profile contains {len(validation_issues)} validation error(s)")

      profile = InstallationProfile.from_dict(data)
      return profile

    except Exception as e:
      console.print(f"\n[prompt.invalid]Failed to load profile from '{source}': {e}[/]")
      raise
