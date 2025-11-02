import subprocess
import os
import getpass
import sys
import re
import json
from src.ansi_codes import green, red, reset, gray, yellow
from src.validations import validate_defaults_json, validate_mirrors_json
from src.types import DefaultsConfig


def info(message: str) -> None:
  print(f"{green}{message}{reset}")


def warning(message: str) -> None:
  print()
  print(f"{yellow}{message}{reset}")


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


def scmd(command: str, stdin_data: str, dry_run: bool = False) -> None:
  """Execute a command with sensitive stdin data without exposing it in process list."""
  if dry_run:
    info(f"{gray}[DRY RUN] {command} (with stdin data)")
    return

  try:
    process = subprocess.Popen(
      command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    stdout, stderr = process.communicate(input=stdin_data)
    if process.returncode != 0:
      raise subprocess.CalledProcessError(process.returncode, command, output=stdout, stderr=stderr)

  except subprocess.CalledProcessError as e:
    error(f"Command '{command}' failed with error: {e}")

    if e.stderr:
      error(f"stderr: {e.stderr}")

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
    prompt = "Choose a username for your new user"
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
    prompt = "Choose a hostname for this system"
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


def load_defaults(distro_id: str = "void") -> DefaultsConfig:
  """Load default values from config.json file for specified distro."""
  config_file = os.path.join(os.path.dirname(__file__), "../config.json")
  try:
    with open(config_file, "r") as f:
      config_data = json.load(f)
      if "defaults" not in config_data or distro_id not in config_data["defaults"]:
        error(f"No defaults found for distro '{distro_id}' in config.json")
        sys.exit(1)

      defaults_data = config_data["defaults"][distro_id]
      data = validate_defaults_json(defaults_data)
      return DefaultsConfig(
        repository=str(data["repository"]),
        timezone=str(data["timezone"]),
        locale=str(data["locale"]),
        keymap=str(data["keymap"]),
        libc=str(data["libc"]),
        ntp=[str(server) for server in data["ntp"]],
      )

  except (FileNotFoundError, json.JSONDecodeError) as e:
    error(f"Error loading config.json: {e}")
    sys.exit(1)

  except (KeyError, ValueError) as e:
    error(f"Invalid config.json format: {e}")
    sys.exit(1)


def load_mirrors(distro_id: str = "void") -> list[tuple[str, str, str]]:
  """Load mirrors from config.json file for specified distro and return as list of (url, region, location) tuples."""
  config_file = os.path.join(os.path.dirname(__file__), "../config.json")
  try:
    with open(config_file, "r") as f:
      config_data = json.load(f)
      if "mirrors" not in config_data or distro_id not in config_data["mirrors"]:
        error(f"No mirrors found for distro '{distro_id}' in config.json")
        sys.exit(1)

      mirrors_data = config_data["mirrors"][distro_id]
      data = validate_mirrors_json(mirrors_data)
      mirrors = [(mirror["url"], mirror["region"], mirror["location"]) for mirror in data]

  except (FileNotFoundError, json.JSONDecodeError) as e:
    error(f"Error loading config.json: {e}")
    sys.exit(1)

  except ValueError as e:
    error(f"Invalid config.json format: {e}")
    sys.exit(1)

  return mirrors


def set_mirror(distro_id: str = "void") -> str:
  """Allow user to select a mirror for the specified distro."""
  default_repository = load_defaults(distro_id)["repository"]
  mirrors = load_mirrors(distro_id)
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


def get_distro_info(file_path: str = "/etc/os-release") -> tuple[str, str]:
  """
  Extract NAME and ID from os-release file.

  Args:
      file_path: Path to os-release file

  Returns:
      Tuple of (name, id) where both default to "Linux"/"linux" if not found

  Raises:
      SystemExit: If file cannot be read
  """
  try:
    with open(file_path, "r") as f:
      name = None
      distro_id = None
      for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
          continue

        if line.startswith("NAME="):
          value = line.split("=", 1)[1]
          # If double quotes, take first word only
          if value.startswith('"') and value.endswith('"'):
            value = value[1:-1].split()[0]
          name = value.capitalize()

        elif line.startswith("ID="):
          value = line.split("=", 1)[1]
          # If double quotes, take first word only
          if value.startswith('"') and value.endswith('"'):
            value = value[1:-1].split()[0]
          distro_id = value.lower()

        if name and distro_id:
          break

      return name or "Linux", distro_id or "linux"

  except (FileNotFoundError, IOError) as e:
    error(f"Failed to read distribution info from {file_path}: {e}")
    sys.exit(1)
