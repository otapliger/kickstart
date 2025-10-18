import subprocess
import os
import getpass
import sys
import re

from src.ansi_codes import green, red, reset, gray


def info(message: str) -> None:
  print(f"{green}{message}{reset}")


def error(message: str) -> None:
  print()
  print(f"{red}{message}{reset}")


def cmd(command: str, dry_run: bool = False) -> None:
  if dry_run:
    info(f"{gray}[DRY RUN] {command}")
    return
  try:
    subprocess.run(command, check=True, shell=True)
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


def set_user() -> str:
  while True:
    user_name = input("Choose a username for your new user: ")
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


def set_host() -> str:
  while True:
    host = input("Choose a hostname for this system: ")
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


def load_defaults() -> dict[str, str]:
  """Load default values from defaults.void file."""
  defaults = {}
  defaults_file = os.path.join(os.path.dirname(__file__), "../config/void/defaults.void")
  required_keys = {"REPOSITORY", "TIMEZONE", "LOCALE", "KEYMAP", "LIBC", "NTP_SERVERS"}

  try:
    with open(defaults_file, "r") as f:
      for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
          key, value = line.split("=", 1)
          defaults[key.strip()] = value.strip()
  except FileNotFoundError:
    error(f"Defaults file not found: {defaults_file}")
    sys.exit(1)

  missing_keys = required_keys - defaults.keys()
  if missing_keys:
    error("Missing required configuration in defaults.void:")
    for key in sorted(missing_keys):
      print(f"  • {key}")
    sys.exit(1)
  return defaults


def load_mirrors() -> list[tuple[str, str, str]]:
  """Load mirrors from mirrors.void file and return as list of (url, region, location) tuples."""
  mirrors = []
  mirrors_file = os.path.join(os.path.dirname(__file__), "../config/void/mirrors.void")

  try:
    with open(mirrors_file, "r") as f:
      for line in f:
        line = line.strip()
        if line and not line.startswith("#"):
          parts = [part.strip() for part in line.split("|")]
          if len(parts) == 3:
            url, region, location = parts
            mirrors.append((url, region, location))
  except FileNotFoundError:
    error(f"Mirrors file not found: {mirrors_file}")
    sys.exit(1)
  return mirrors


def set_mirror() -> str:
  """Allow user to select a Void Linux mirror."""
  mirrors = load_mirrors()

  if not mirrors:
    error("No mirrors available. Using default.")
    return load_defaults()["REPOSITORY"]

  print("Available mirrors:")
  for i, (url, region, location) in enumerate(mirrors, start=1):
    if url == load_defaults()["REPOSITORY"]:
      print(f"  {i}. {region} - {location} (default)")
    else:
      print(f"  {i}. {region} - {location}")

  while True:
    try:
      print()
      choice = input("Select a mirror (press Enter for default): ").strip()

      if not choice:
        # Return default from config
        return load_defaults()["REPOSITORY"]

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
