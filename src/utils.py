import subprocess
import os
import getpass
import sys
import re
import json
from typing import Any, TypedDict
from src.ansi_codes import green, red, reset, gray


def info(message: str) -> None:
  print(f"{green}{message}{reset}")


class DefaultsConfig(TypedDict):
  repository: str
  timezone: str
  locale: str
  keymap: str
  libc: str
  ntp: list[str]


class MirrorData(TypedDict):
  url: str
  region: str
  location: str


def error(message: str) -> None:
  print()
  print(f"{red}{message}{reset}")


def cmd(command: str, dry_run: bool = False) -> None:
  if dry_run:
    info(f"{gray}[DRY RUN] {command}")
    return
  try:
    _ = subprocess.run(command, check=True, shell=True)
  except subprocess.CalledProcessError as e:
    error(f"Command '{command}' failed with error: {e}")
    sys.exit(1)


def write(path: str, lines: list[str], dry_run: bool = False) -> None:
  assert isinstance(lines, list)
  if dry_run:
    info(f"{gray}[DRY RUN] Writing to {path}:")
    for line in lines:
      print(f"{gray}  {line}{reset}")
    return
  open(path, "w").close()
  with open(path, "a") as f:
    for line in lines:
      print(line, file=f)


def set_user(default: str | None = None) -> str:
  while True:
    prompt = f"Choose a username for your new user"
    if default:
      prompt += f" [{default}]"
    prompt += ": "
    user_name = input(prompt)
    if not user_name and default:
      user_name = default
    if not user_name:
      error("A username is required to continue.")
      continue
    return user_name


def set_pass(user_name: str) -> str:
  while True:
    user_pass = getpass.getpass(f"Create a password for '{user_name}': ")
    if not user_pass:
      error("Password cannot be empty. Please enter a password.")
      continue
    user_pass_check = getpass.getpass("Re-enter the password to confirm: ")
    if user_pass != user_pass_check:
      error("Passwords don't match. Please try again.")
      continue
    print()
    return user_pass


def set_host(default: str | None = None) -> str:
  while True:
    prompt = f"Choose a hostname for this system"
    if default:
      prompt += f" [{default}]"
    prompt += ": "
    host = input(prompt)
    if not host and default:
      host = default
    if not host:
      error("A hostname is required to continue.")
      continue
    print()
    return host


def set_disk() -> str:
  while True:
    disks = [disk for disk in os.listdir("/dev") if re.match(r"^(nvme\d+n\d+|sd[a-z]+|vd[a-z]+|disk\d+)$", disk)]
    print("Disks:")
    for i, disk in enumerate(disks, start=1):
      print(f"  {i}. /dev/{disk}")
    try:
      print()
      disk_choice = int(input("Select the destination disk: "))
    except ValueError:
      error("Invalid input. Please enter a number corresponding to the disk.")
      continue
    if disk_choice < 1 or disk_choice > len(disks):
      error("Invalid selection. Please choose a valid disk number.")
      continue
    return f"/dev/{disks[disk_choice - 1]}"


def set_luks() -> str:
  while True:
    luks_pass = getpass.getpass("Set a password for the disk encryption: ")
    if not luks_pass:
      error("You need to enter a password for the disk encryption, please try again.")
      continue
    luks_pass_check = getpass.getpass("Verify the password: ")
    if luks_pass != luks_pass_check:
      error("Passwords don't match, please try again.")
      continue
    print()
    return luks_pass


def _validate_defaults_json(data: Any) -> dict[str, Any]:
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


def load_defaults() -> DefaultsConfig:
  """Load default values from defaults.json file."""
  defaults_file = os.path.join(os.path.dirname(__file__), "../config/void/defaults.json")
  try:
    with open(defaults_file, "r") as f:
      defaults_data = json.load(f)
      data = _validate_defaults_json(defaults_data)
      return DefaultsConfig(
        repository=str(data["repository"]),
        timezone=str(data["timezone"]),
        locale=str(data["locale"]),
        keymap=str(data["keymap"]),
        libc=str(data["libc"]),
        ntp=[str(server) for server in data["ntp"]],
      )
  except (FileNotFoundError, json.JSONDecodeError) as e:
    error(f"Error loading defaults.json: {e}")
    sys.exit(1)
  except (KeyError, ValueError) as e:
    error(f"Invalid defaults.json format: {e}")
    sys.exit(1)


def _validate_mirrors_json(data: Any) -> list[MirrorData]:
  """Validate and return mirrors JSON data with proper typing."""
  if not isinstance(data, list):
    raise ValueError("Mirrors JSON must be an array")
  for item in data:
    if not isinstance(item, dict):
      raise ValueError("Each mirror must be an object")
    if not all(key in item for key in ["url", "region", "location"]):
      raise ValueError("Each mirror must have url, region, and location fields")
  return data


def load_mirrors() -> list[tuple[str, str, str]]:
  """Load mirrors from mirrors.json file and return as list of (url, region, location) tuples."""
  mirrors_file = os.path.join(os.path.dirname(__file__), "../config/void/mirrors.json")
  try:
    with open(mirrors_file, "r") as f:
      mirrors_data = json.load(f)
      data = _validate_mirrors_json(mirrors_data)
      mirrors = [(mirror["url"], mirror["region"], mirror["location"]) for mirror in data]
  except (FileNotFoundError, json.JSONDecodeError) as e:
    error(f"Error loading mirrors.json: {e}")
    sys.exit(1)
  except ValueError as e:
    error(f"Invalid mirrors.json format: {e}")
    sys.exit(1)
  return mirrors


def set_mirror() -> str:
  """Allow user to select a Void Linux mirror."""
  default_repository = load_defaults()["repository"]
  mirrors = load_mirrors()
  if not mirrors:
    error("No mirrors available. Using default.")
    return str(default_repository)
  print("Available mirrors:")
  for i, (url, region, location) in enumerate(mirrors, start=1):
    if url == default_repository:
      print(f"  {i}. {region} - {location} (default)")
    else:
      print(f"  {i}. {region} - {location}")
  while True:
    try:
      print()
      choice = input("Select a mirror (press Enter for default): ").strip()
      if not choice:
        return default_repository
      mirror_choice = int(choice)
      if 1 <= mirror_choice <= len(mirrors):
        selected_url = mirrors[mirror_choice - 1][0]
        print(f"Selected: {selected_url}")
        print()
        return selected_url
      else:
        error(f"Invalid selection. Please choose between 1 and {len(mirrors)}.")
    except ValueError:
      error("Invalid input. Please enter a number or press Enter for default.")
