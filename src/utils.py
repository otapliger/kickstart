import subprocess
import os
import getpass
import sys
import re
import json
from io import StringIO
from operator import itemgetter
from src.ansi_codes import green, red, reset, gray, yellow
from src.validations import validate_defaults_json, validate_mirrors_json
from src.types import DefaultsConfig, GPUVendor


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


def write(lines: list[str], path: str, dry_run: bool = False) -> None:
  assert isinstance(lines, list)
  if dry_run:
    info(f"{gray}[DRY RUN] Writing to {path}:")
    for line in lines:
      print(f"{gray}{line}{reset}")
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


def load_defaults(distro_id: str) -> DefaultsConfig:
  """Load default values from config.json file for specified distro."""
  config_file = os.path.join(os.path.dirname(__file__), "../config.json")
  try:
    with open(config_file, "r") as f:
      config_data = json.load(f)
      if "defaults" not in config_data or distro_id not in config_data["defaults"]:
        return DefaultsConfig(
          repository="https://example.com/repo",
          timezone="Europe/London",
          locale="en_GB.UTF-8",
          keymap="uk",
          libc="glibc",
          ntp=["0.pool.ntp.org", "1.pool.ntp.org", "2.pool.ntp.org", "3.pool.ntp.org"],
        )

      defaults_data = config_data["defaults"][distro_id]
      data = validate_defaults_json(defaults_data)

      # Use dictionary comprehension to convert values to strings
      # except ntp list
      return DefaultsConfig(
        **{k: str(v) for k, v in data.items() if k != "ntp"},
        ntp=[str(server) for server in data["ntp"]],
      )

  except (FileNotFoundError, json.JSONDecodeError) as e:
    error(f"Error loading config.json: {e}")
    sys.exit(1)

  except (KeyError, ValueError) as e:
    error(f"Invalid config.json format: {e}")
    sys.exit(1)


def load_mirrors(distro_id: str) -> list[tuple[str, str, str]]:
  """Load mirrors from config.json file for specified distro and return as list of (url, region, location) tuples."""
  config_file = os.path.join(os.path.dirname(__file__), "../config.json")

  try:
    with open(config_file, "r") as f:
      config_data = json.load(f)
      if "mirrors" not in config_data or distro_id not in config_data["mirrors"]:
        return [("https://example.com/repo", "Global", "Generic Mirror")]

      mirrors_data = config_data["mirrors"][distro_id]
      data = validate_mirrors_json(mirrors_data)
      extract_mirror = itemgetter("url", "region", "location")
      mirrors = list(map(extract_mirror, data))

  except (FileNotFoundError, json.JSONDecodeError) as e:
    error(f"Error loading config.json: {e}")
    sys.exit(1)

  except ValueError as e:
    error(f"Invalid config.json format: {e}")
    sys.exit(1)

  return mirrors


def set_mirror(distro_id: str) -> str:
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
      default_mirror = next(
        (f"{region} - {location}" for url, region, location in mirrors if url == default_repository), "default"
      )
      choice = input(f"Select a mirror [{default_mirror}]: ").strip()
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


def detect_gpu_vendors(warnings: list[str] | None = None) -> list[GPUVendor]:
  """
  Detect GPU vendors present in the system by examining lspci output.

  Args:
      warnings: Optional list to collect warnings (dry mode only)

  Returns:
      List of GPUVendor enums representing detected GPUs
  """
  try:
    result = subprocess.run(["lspci", "-nn"], capture_output=True, text=True, check=False)

    if result.returncode != 0:
      warning_msg = f"lspci command failed (exit code {result.returncode}). Unable to detect GPU."
      if warnings is not None:
        warnings.append(warning_msg)
      return [GPUVendor.UNKNOWN]

    output = result.stdout.lower()

    # Filter for GPU-related lines
    gpu_lines = filter(
      lambda line: any(x in line for x in ["vga compatible controller", "3d controller", "display controller"]),
      output.splitlines(),
    )

    vendor_checks = [
      (lambda line: "intel" in line, GPUVendor.INTEL),
      (lambda line: any(x in line for x in ["amd", "ati", "advanced micro devices"]), GPUVendor.AMD),
      (lambda line: any(x in line for x in ["nvidia", "geforce", "quadro", "tesla"]), GPUVendor.NVIDIA),
    ]

    # Detect vendors using set comprehension to avoid duplicates
    vendors = list({vendor for line in gpu_lines for predicate, vendor in vendor_checks if predicate(line)})
    return vendors or [GPUVendor.UNKNOWN]

  except FileNotFoundError:
    warning_msg = "Install pciutils to enable GPU detection"
    if warnings is not None:
      warnings.append(warning_msg)
    return [GPUVendor.UNKNOWN]

  except Exception as e:
    warning_msg = f"Unexpected error detecting GPU - {e}"
    if warnings is not None:
      warnings.append(warning_msg)
    return [GPUVendor.UNKNOWN]


def get_gpu_packages(
  distro_id: str, vendors: list[GPUVendor] | None = None, warnings: list[str] | None = None
) -> list[str]:
  """
  Get the appropriate GPU driver packages for a distro based on detected vendors.

  Args:
      distro_id: Distribution identifier
      vendors: Optional list of GPU vendors

  Returns:
      List of package names for the detected GPU vendors
  """
  if vendors is None:
    vendors = detect_gpu_vendors(warnings)

  config_file = os.path.join(os.path.dirname(__file__), "../config.json")

  with open(config_file, "r") as f:
    config_data = json.load(f)

    if "gpu_packages" not in config_data:
      return []

    if distro_id not in config_data["gpu_packages"]:
      return []

    gpu_config = config_data["gpu_packages"][distro_id]

  vendor_key_map = {
    GPUVendor.INTEL: "intel",
    GPUVendor.AMD: "amd",
    GPUVendor.NVIDIA: "nvidia",
    GPUVendor.UNKNOWN: "unknown",
  }

  packages = {
    pkg
    for vendor in vendors
    if (vendor_key := vendor_key_map.get(vendor))
    if vendor_key in gpu_config
    for pkg in gpu_config[vendor_key]
    if isinstance(gpu_config[vendor_key], list)
  }

  return sorted(packages)


def print_detected_gpus(vendors: list[GPUVendor]) -> None:
  """
  Print detected GPU vendors in a user-friendly format.

  Args:
      vendors: List of detected GPU vendors
  """
  if not vendors or vendors == [GPUVendor.UNKNOWN]:
    info("No specific GPU detected, will use generic drivers.")
    return

  info("Detected GPU(s):")
  for vendor in vendors:
    if vendor == GPUVendor.INTEL:
      print("  - Intel GPU")
    elif vendor == GPUVendor.AMD:
      print("  - AMD GPU")
    elif vendor == GPUVendor.NVIDIA:
      print("  - NVIDIA GPU")


def collect_header_lines(distro_id: str, dry_mode: bool = False) -> list[str]:
  """
  Collect all header content (logo, dry run message) into a list of lines.

  Args:
      distro_id: Distribution identifier for logo selection
      dry_mode: Whether dry run mode is enabled

  Returns:
      List of strings representing each line of the header
  """
  from src.ascii_art import print_logo
  from src.ansi_codes import bold

  lines = []
  last_stdout = sys.stdout
  sys.stdout = StringIO()
  print_logo(distro_id)
  logo_output = sys.stdout.getvalue()
  sys.stdout = last_stdout
  lines.extend(logo_output.rstrip("\n").split("\n"))

  if dry_mode:
    lines.append(f"{yellow}{bold}DRY RUN MODE{reset} - No actual changes will be made to your system")
  lines.append("")

  return lines


def format_step_name(name: str) -> str:
  """
  Format step name from function name string.

  Args:
      name: Step function name

  Returns:
      Formatted step name (e.g., "Settings")
  """
  return name.replace("step_", "").replace("_", " ").title().lstrip("0123456789 ")
