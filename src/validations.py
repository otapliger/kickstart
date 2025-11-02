"""
Validation functions for void.kickstart.

This module contains all validation functions used throughout the application
for validating URLs, timezones, locales, hostnames, profiles, and JSON data.
"""

import re
import urllib.parse
from pathlib import Path
from typing import Any
from src.types import MirrorData


# =============================================================================
# Type Guards
# =============================================================================
# Functions that check types and return boolean results for type narrowing


def is_string_list(value: object) -> bool:
  """Type guard to check if value is a list of strings."""
  return isinstance(value, list) and all(isinstance(item, str) for item in value)


# =============================================================================
# Validation Functions
# =============================================================================
# Functions that validate data and return boolean or list of issues


def validate_url(url: str) -> bool:
  """Validate that a URL is properly formatted."""
  if not url:
    return False

  result = urllib.parse.urlparse(url)
  return bool(result.scheme and result.netloc)


def validate_timezone(timezone: str) -> bool:
  """Validate timezone against common timezone patterns."""
  if "/" not in timezone:
    return False

  parts = timezone.split("/")
  if len(parts) != 2:
    return False

  region, city = parts
  if not region.replace("_", "").isalpha() or not city.replace("_", "").isalpha():
    return False

  return True


def validate_locale(locale: str) -> bool:
  """Validate locale format - supports various glibc locale formats."""
  if not locale:
    return False

  # Allow C/POSIX locales
  if locale in ("C", "POSIX"):
    return True

  # Basic pattern: language[_territory][.encoding][@modifier]
  # Examples: en, en_US, en_US.UTF-8, en_US@euro, de_DE.ISO-8859-1@euro
  pattern = r"^[a-z]{2,3}(_[A-Z]{2})?(\.[A-Za-z0-9_-]+)?(@[A-Za-z0-9_-]+)?$"
  return bool(re.match(pattern, locale))


def validate_libc(libc: str) -> bool:
  """Validate C library implementation."""
  valid_libcs = {"glibc", "musl"}
  return libc.lower() in valid_libcs


def validate_hostname(hostname: str) -> bool:
  """Validate hostname format according to RFC 1123."""
  if not hostname or len(hostname) > 253:
    return False

  labels = hostname.split(".")
  for label in labels:
    if not label or len(label) > 63:
      return False

    if not (label[0].isalnum() and label[-1].isalnum()):
      return False

    if not all(c.isalnum() or c == "-" for c in label):
      return False

  return True


def validate_profile(source: str) -> bool:
  """Validate profile source path or URL. Returns True if valid, False if invalid."""
  if source.startswith(("http://", "https://")):
    return True

  else:
    return Path(source).exists()


def validate_profile_json(data: dict[str, object]) -> list[str]:
  """
  Validate profile JSON structure and return list of issues.

  Returns empty list if valid, list of error messages if invalid.
  """
  issues: list[str] = []

  # Required fields
  if not isinstance(data.get("name"), str):
    issues.append("Profile must have a 'name' field as string")

  if not isinstance(data.get("description"), str):
    issues.append("Profile must have a 'description' field as string")

  # Optional but validated fields
  config = data.get("config", {})
  if config is not None and not isinstance(config, dict):
    issues.append("'config' field must be an object")

  packages = data.get("packages", {})
  if packages is not None and not isinstance(packages, dict):
    issues.append("'packages' field must be an object")

  # Validate config values if present
  if isinstance(config, dict):
    libc = config.get("libc")
    if libc is not None and libc not in ["glibc", "musl"]:
      issues.append("config.libc must be 'glibc' or 'musl'")

  # Validate package structure if present
  if isinstance(packages, dict):
    for field in ["additional", "exclude"]:
      value = packages.get(field)

      if value is not None and not isinstance(value, list):
        issues.append(f"packages.{field} must be a list")

      elif isinstance(value, list) and not all(isinstance(item, str) for item in value):
        issues.append(f"packages.{field} must be a list of strings")

  return issues


def validate_defaults_json(data: Any) -> dict[str, Any]:
  """Validate and return defaults JSON data with proper typing."""
  if not isinstance(data, dict):
    raise ValueError("Defaults JSON must be an object")

  required_keys = {"repository", "timezone", "locale", "keymap", "libc", "ntp"}
  missing_keys = required_keys - data.keys()
  if missing_keys:
    raise KeyError(f"Missing required keys: {missing_keys}")

  if not isinstance(data["ntp"], list):
    raise ValueError("ntp field must be a list")

  return data


def validate_mirrors_json(data: Any) -> list[MirrorData]:
  """Validate and return mirrors JSON data with proper typing."""
  if not isinstance(data, list):
    raise ValueError("Mirrors JSON must be an array")

  for item in data:
    if not isinstance(item, dict):
      raise ValueError("Each mirror must be an object")

    if not all(key in item for key in ["url", "region", "location"]):
      raise ValueError("Each mirror must have url, region, and location fields")

  return data


def validate_config_json(data: Any, distro_id: str) -> None:
  """Validate unified config.json structure for a specific distro.

  Args:
      data: The parsed JSON data
      distro_id: The distribution ID to validate (e.g., 'void')

  Raises:
      ValueError: If the structure is invalid
      KeyError: If required keys are missing
  """
  if not isinstance(data, dict):
    raise ValueError("Config JSON must be an object")

  # Validate top-level keys
  required_sections = {"defaults", "mirrors", "packages"}
  if not all(section in data for section in required_sections):
    missing = required_sections - data.keys()
    raise KeyError(f"Missing required sections: {missing}")

  # Validate distro exists in each section
  if distro_id not in data["defaults"]:
    raise KeyError(f"Distro '{distro_id}' not found in defaults section")

  if distro_id not in data["mirrors"]:
    raise KeyError(f"Distro '{distro_id}' not found in mirrors section")

  if distro_id not in data["packages"]:
    raise KeyError(f"Distro '{distro_id}' not found in packages section")

  # Validate defaults structure
  _ = validate_defaults_json(data["defaults"][distro_id])

  # Validate mirrors structure
  _ = validate_mirrors_json(data["mirrors"][distro_id])

  # Validate packages structure
  if not isinstance(data["packages"][distro_id], list):
    raise ValueError(f"Packages for '{distro_id}' must be a list")

  if not all(isinstance(pkg, str) for pkg in data["packages"][distro_id]):
    raise ValueError(f"All packages for '{distro_id}' must be strings")


def validate_cli_arguments(
  repository: str,
  timezone: str,
  locale: str,
  libc: str,
  hostname: str | None = None,
  profile: str | None = None,
) -> list[str]:
  """
  Validate all command line arguments and return list of error messages.

  Returns empty list if all arguments are valid, list of error messages otherwise.
  """
  errors: list[str] = []

  if not validate_url(repository):
    errors.append(f"Invalid repository URL: {repository}")

  if not validate_timezone(timezone):
    errors.append(f"Invalid timezone: {timezone} (expected format: Region/City)")

  if not validate_locale(locale):
    errors.append(f"Invalid locale: {locale} (expected format: language[_COUNTRY][.encoding][@modifier])")

  if not validate_libc(libc):
    errors.append(f"Invalid libc: {libc} (must be 'glibc' or 'musl')")

  if hostname and not validate_hostname(hostname):
    errors.append(f"Invalid hostname: {hostname} (must follow RFC 1123 format)")

  if profile and not validate_profile(profile):
    errors.append(f"Profile file not found: {profile}")

  return errors
