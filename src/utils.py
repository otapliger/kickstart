import subprocess
import os
import sys
import re
import json
from operator import itemgetter
from rich.console import Console
from src.validations import validate_defaults_json, validate_mirrors_json
from src.input import HostnamePrompt, IntegerPrompt, UsernamePrompt, PasswordPrompt
from src.types import DefaultsConfig, GPUVendor
from src.tui import TUI

console = Console()


def get_resource_path(relative_path: str) -> str:
  """
  Get absolute path to resource for both normal execution and Nuitka binaries.
  For Nuitka --onefile mode, files are extracted to a temporary directory.
  """
  if getattr(sys, "frozen", False):
    # Running as Nuitka binary - use executable's directory or _MEIPASS
    if hasattr(sys, "_MEIPASS"):
      base_path = sys._MEIPASS
    else:
      # Fallback: use the directory containing the frozen executable
      base_path = os.path.dirname(sys.executable)
  else:
    # Running as normal Python script
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

  return os.path.join(base_path, relative_path)


def cmd(command: str, dry_run: bool, ui: TUI) -> None:
  if dry_run:
    message = f"[bold green][dim][DRY RUN] {command}[/][/]"
    ui.print(message)
    return

  try:
    _ = subprocess.run(command, check=True, shell=True)

  except subprocess.CalledProcessError as e:
    console.print(f"\n[bold red]Command '{command}' failed with error: {e}[/]")
    sys.exit(1)


def scmd(command: str, stdin_data: str, dry_run: bool, ui: TUI) -> None:
  """Execute a command with sensitive stdin data without exposing it in process list."""
  if dry_run:
    message = f"[bold green][dim][DRY RUN] {command} (with stdin data)[/][/]"
    ui.print(message)
    return

  try:
    process = subprocess.Popen(
      command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    stdout, stderr = process.communicate(input=stdin_data)
    if process.returncode != 0:
      raise subprocess.CalledProcessError(process.returncode, command, output=stdout, stderr=stderr)

  except subprocess.CalledProcessError as e:
    console.print(f"\n[bold red]Command '{command}' failed with error: {e}[/]")

    if e.stderr:
      console.print(f"\n[bold red]stderr: {e.stderr}[/]")

    sys.exit(1)


def write(lines: list[str], path: str, dry_run: bool, ui: TUI) -> None:
  assert isinstance(lines, list)
  if dry_run:
    message = f"[bold green][dim][DRY RUN] Writing to {path}:[/][/]"
    ui.print(message)
    for line in lines:
      ui.print(f"[dim]{line}[/]")
    return

  open(path, "w").close()
  with open(path, "a") as f:
    for line in lines:
      print(line, file=f)


def set_host(default: str | None = None) -> str:
  host = HostnamePrompt.ask("Enter a hostname for the system", default=default)
  return host


def set_disk() -> tuple[str, str]:
  while True:
    console.print()
    disks_regex = r"^(nvme\d+n\d+|sd[a-z]+|vd[a-z]+|disk\d+)$"
    disks = [disk for disk in os.listdir("/dev") if re.match(disks_regex, disk)]

    console.print("Disks:")
    for i, disk in enumerate(disks, start=1):
      console.print(f" {i}. /dev/{disk}")

    console.print()
    choices = [str(i) for i in range(1, len(disks) + 1)]
    disk_choice = IntegerPrompt.ask("Choose the destination disk (enter number)", choices=choices)
    luks_pass = PasswordPrompt.ask("Set disk encryption password (hidden)")
    return f"/dev/{disks[disk_choice - 1]}", luks_pass


def set_user() -> tuple[str, str]:
  while True:
    console.print()
    user_name = UsernamePrompt.ask("Enter username for the new account")
    user_pass = PasswordPrompt.ask("Provide user password (hidden)")
    return user_name, user_pass


def set_mirror(distro_id: str) -> str:
  default_repository = load_defaults(distro_id)["repository"]
  mirrors = load_mirrors(distro_id)
  if not mirrors:
    console.print("\n[bold red]No mirrors available. Using default.[/]")
    return str(default_repository)

  console.print()
  console.print("Available mirrors:")
  for i, (_url, region, location) in enumerate(mirrors, start=1):
    console.print(f" {i}. {location} ({region})")

  console.print()
  choices = [str(i) for i in range(1, len(mirrors) + 1)]
  mirror_choice = IntegerPrompt.ask("Choose a mirror (enter number)", choices=choices, default=1)
  selected_url = mirrors[mirror_choice - 1][0]
  return selected_url


def load_defaults(distro_id: str) -> DefaultsConfig:
  """Load default values from config.json file for specified distro."""
  config_file = get_resource_path("config.json")
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
    console.print(f"\n[bold red]Error loading config.json: {e}[/]")
    sys.exit(1)

  except (KeyError, ValueError) as e:
    console.print(f"\n[bold red]Invalid config.json format: {e}[/]")
    sys.exit(1)


def load_mirrors(distro_id: str) -> list[tuple[str, str, str]]:
  """Load mirrors from config.json file for specified distro and return as list of (url, region, location) tuples."""
  config_file = get_resource_path("config.json")

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
    console.print(f"\n[bold red]Error loading config.json: {e}[/]")
    sys.exit(1)

  except ValueError as e:
    console.print(f"\n[bold red]Invalid config.json format: {e}[/]")
    sys.exit(1)

  return mirrors


def get_distro_info(file_path: str = "/etc/os-release") -> tuple[str, str]:
  """
  Extract NAME and ID from os-release file.

  Args:
      file_path: Path to os-release file

  Returns:
      Tuple of (name, id) where both default to "Linux"/"linux" if not found
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

  except (FileNotFoundError, IOError):
    return "Linux", "linux"


def get_gpu_packages(distro_id: str, warnings: list[str] | None = None) -> list[str]:
  """
  Get the appropriate GPU driver packages for a distro based on detected vendors.

  Args:
      distro_id: Distribution identifier
      warnings: Optional list to append warnings (used when detection fails or tools are unavailable).

  Returns:
      Sorted list of unique package names (strings) recommended for detected GPU vendors.
      Returns an empty list if no GPU package mappings are available for the given distro.
  """
  vendors = detect_gpu_vendors(warnings)

  config_file = get_resource_path("config.json")

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
      if warnings is not None:
        warnings.append(f"lspci failed (exit {result.returncode}) - GPU detection skipped")
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
    if warnings is not None:
      warnings.append("Install pciutils to enable GPU detection")
    return [GPUVendor.UNKNOWN]


def format_step_name(name: str) -> str:
  """
  Format step name from function name string.

  Args:
      name: Step function name

  Returns:
      Formatted step name (e.g., "Settings")
  """
  return name.replace("step_", "").replace("_", " ").title().lstrip("0123456789 ")
