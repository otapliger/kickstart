import subprocess
import os
import getpass
import sys
import re
from typing import Optional
from argparse import Namespace
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


def write(path: str, lines: list[str]) -> None:
  assert isinstance(lines, list)
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


class InstallerContext:
  def __init__(self, args: Namespace) -> None:
    self.args: Namespace = args
    self.host: Optional[str] = None
    self.disk: Optional[str] = None
    self.luks_pass: Optional[str] = None
    self.user_name: Optional[str] = None
    self.user_pass: Optional[str] = None
    self.cryptroot: Optional[str] = None
    self.esp: Optional[str] = None
    self.root: Optional[str] = None
