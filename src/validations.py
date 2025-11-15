"""
Validation functions for kickstart.

This module contains all validation functions used throughout the application
for validating URLs, timezones, locales, hostnames, profiles, and JSON data.
"""

import re
import urllib.parse
from pathlib import Path
from typing import Any, TypedDict


class MirrorData(TypedDict):
  url: str
  region: str
  location: str


# =============================================================================
# Validation Functions
# =============================================================================
# Functions that validate data and return boolean or list of issues


def validate_username(username: str) -> bool:
  max_len = 32

  if not username:
    return False
  if username[0] == "":
    return False
  if username[0] == "-":
    return False
  if len(username) > max_len:
    return False
  if username.isdigit():
    return False

  def _make_username_pattern() -> re.Pattern[str]:
    start_chars = "a-z_"
    body_chars = start_chars + "0-9-"
    pattern = rf"^[{start_chars}][{body_chars}]{{0,{max_len - 1}}}$"
    return re.compile(pattern)

  pattern = _make_username_pattern()
  return bool(pattern.fullmatch(username))


def validate_password(password: str) -> bool:
  return len(password.strip()) > 1


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

  def is_valid_label(label: str) -> bool:
    return (
      bool(label)
      and len(label) <= 63
      and label[0].isalnum()
      and label[-1].isalnum()
      and all(c.isalnum() or c == "-" for c in label)
    )

  return all(is_valid_label(label) for label in labels)


def validate_profile(source: str, distro_id: str | None = None) -> bool:
  """Validate profile source (name, path, or URL). Returns True if valid, False if invalid."""
  if source.startswith(("http://", "https://")):
    return True

  if distro_id and not source.startswith(("http://", "https://", "/", "./")):
    from src.registry import get_embedded_profile

    if get_embedded_profile(distro_id, source):
      return True

  return Path(source).exists()


def validate_profile_json(data: dict[str, object]) -> list[str]:
  """
  Validate profile JSON structure and return list of issues.

  Returns empty list if valid, list of error messages if invalid.
  """
  required_validators = [
    (lambda: isinstance(data.get("name"), str), "Profile must have a 'name' field as string"),
    (lambda: isinstance(data.get("description"), str), "Profile must have a 'description' field as string"),
    (lambda: isinstance(data.get("distro"), str), "Profile must have a 'distro' field as string"),
  ]

  issues = [msg for validator, msg in required_validators if not validator()]

  # Optional but validated fields
  config = data.get("config", {})
  if config is not None and not isinstance(config, dict):
    issues.append("'config' field must be an object")

  packages = data.get("packages", {})
  if packages is not None and not isinstance(packages, dict):
    issues.append("'packages' field must be an object")

  if isinstance(config, dict):
    libc = config.get("libc")
    if libc is not None and libc not in ["glibc", "musl"]:
      issues.append("config.libc must be 'glibc' or 'musl'")

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

  required_keys = {"timezone", "locale", "keymap", "libc", "ntp"}
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


def validate_cli_arguments(
  repository: str | None,
  timezone: str,
  locale: str,
  libc: str,
  hostname: str | None = None,
  profile: str | None = None,
  distro_id: str | None = None,
) -> list[str]:
  """
  Validate all command line arguments and return list of error messages.

  Returns empty list if all arguments are valid, list of error messages otherwise.
  """
  # Define validators as (condition, error_message) tuples
  validators = [
    (validate_timezone(timezone), f"Invalid timezone: {timezone} (expected format: Region/City)"),
    (validate_locale(locale), f"Invalid locale: {locale} (expected format: language[_COUNTRY][.encoding][@modifier])"),
    (validate_libc(libc), f"Invalid libc: {libc} (must be 'glibc' or 'musl')"),
  ]

  if repository:
    validators.append((validate_url(repository), f"Invalid repository URL: {repository}"))

  if hostname:
    validators.append((validate_hostname(hostname), f"Invalid hostname: {hostname} (must follow RFC 1123 format)"))

  if profile:
    validators.append((validate_profile(profile, distro_id), f"Profile not found: {profile}"))

  return [msg for valid, msg in validators if not valid]
