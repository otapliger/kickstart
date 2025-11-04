import subprocess
import sys
from typing import Callable
from rich.console import Console
from rich.prompt import Confirm
from src.context import InstallerContext
from src.chroot import generate_chroot
from src.distros import get_distro
from src.utils import (
  cmd,
  scmd,
  write,
  set_disk,
  set_host,
  set_luks,
  set_pass,
  set_user,
  set_mirror,
  load_defaults,
)

console = Console()


def step_01_settings(ctx: InstallerContext, _warnings: list[str]) -> None:
  config_items = [
    ("C library", ctx.config.libc),
    ("Keymap", ctx.config.keymap),
    ("Locale", ctx.config.locale),
    ("Timezone", ctx.config.timezone),
  ]

  # Initialize TUI
  if ctx.ui:
    ctx.ui.initialize()

  # Print config information
  if ctx.dry:
    console.print("Skipping root and system checks in dry run mode")
    console.print()

  for label, value in config_items:
    console.print(f" • {label}: {value}")
  console.print()

  # Select hostname: CLI > profile > interactive
  # fmt: off
  ctx.host = (
    ctx.config.hostname
    or (ctx.profile.hostname if ctx.profile else None)
    or set_host(ctx.distro_id)
  )
  # fmt: on

  ctx.disk = set_disk()
  ctx.luks_pass = set_luks()
  ctx.user_name = set_user()
  ctx.user_pass = set_pass(ctx.user_name)

  # Select repository: profile > CLI > interactive
  profile_repo = ctx.profile.config.repository if ctx.profile else None

  if profile_repo:
    ctx.repository = profile_repo
    console.print(f"Using repository from profile: {ctx.repository}")

  elif ctx.config.repository is not None:
    ctx.repository = ctx.config.repository
    console.print(f"Using repository from command line: {ctx.repository}")

  else:
    ctx.repository = set_mirror(ctx.distro_id)

  console.print(f"\n[bold yellow]WARNING:[/] All data on {ctx.disk} will be erased.", style="bold")
  response = Confirm.ask("Are you sure you want to continue?", default=False)
  if not response:
    console.print("\n[bold red]Installation aborted. No changes were made to the system.[/]")
    sys.exit(0)

  console.print()

  ctx.cryptroot = "/dev/disk/by-partlabel/ENCRYPTED"
  ctx.esp = "/dev/disk/by-partlabel/ESP"
  ctx.root = f"/dev/mapper/{ctx.host}"


def step_02_disk_setup(ctx: InstallerContext, _warnings: list[str]) -> None:
  cmd(f"wipefs -af {ctx.disk}", ctx.dry)
  cmd(f"sgdisk -Zo {ctx.disk}", ctx.dry)
  cmd(f"parted -s {ctx.disk} mklabel gpt", ctx.dry)
  cmd(f"parted -s {ctx.disk} mkpart ESP fat32 1MiB 513MiB", ctx.dry)
  cmd(f"parted -s {ctx.disk} mkpart ENCRYPTED 513MiB 100%", ctx.dry)
  cmd(f"parted -s {ctx.disk} set 1 esp on", ctx.dry)
  cmd(f"partprobe {ctx.disk}", ctx.dry)
  cmd(f"mkfs.vfat -F32 -n ESP {ctx.esp}", ctx.dry)

  assert ctx.luks_pass is not None
  scmd(f"cryptsetup luksFormat --type luks1 --pbkdf-force-iterations 1000 {ctx.cryptroot} -d -", ctx.luks_pass, ctx.dry)
  scmd(f"cryptsetup luksOpen {ctx.cryptroot} {ctx.host} -d -", ctx.luks_pass, ctx.dry)
  cmd(f"mkfs.btrfs -L {ctx.host} {ctx.root}", ctx.dry)
  cmd(f"mount -o compress=zstd,noatime {ctx.root} /mnt", ctx.dry)

  subvols = ["", "home", "snapshots", "var_cache", "var_log"]
  for name in (f"/mnt/@{sub}" if sub else "/mnt/@" for sub in subvols):
    cmd(f"btrfs subvolume create {name}", ctx.dry)

  cmd("umount /mnt", ctx.dry)

  mount_base = "mount -o X-mount.mkdir,compress=zstd,noatime,subvol=@"

  mount_points = [
    ("", "/mnt"),
    ("snapshots", "/mnt/.snapshots"),
    ("var_cache", "/mnt/var/cache"),
    ("var_log", "/mnt/var/log"),
    ("home", "/mnt/home"),
  ]

  for subvol, path in mount_points:
    cmd(f"{mount_base}{subvol} {ctx.root} {path}", ctx.dry)

  cmd("mkdir -p /mnt/boot/efi", ctx.dry)
  cmd(f"mount {ctx.esp} /mnt/boot/efi", ctx.dry)


def step_03_system_bootstrap(ctx: InstallerContext, _warnings: list[str]) -> None:
  distro = get_distro(ctx.distro_id, ctx.dry)

  for prep_cmd in distro.prepare_base_system():
    cmd(prep_cmd, ctx.dry)

  base_pkgs = ["base", "linux"] if ctx.dry else distro.base_packages()
  cmd(distro.install_base_system(base_pkgs, ctx.repository), ctx.dry)


def step_04_system_installation_and_configuration(ctx: InstallerContext, warnings: list[str]) -> None:
  efi_uuid = (
    "DRY-RUN-EFI-UUID"
    if ctx.dry
    else subprocess.run(
      "blkid --match-tag UUID --output value /dev/disk/by-partlabel/ESP",
      check=True,
      shell=True,
      capture_output=True,
      text=True,
    ).stdout.strip()
  )

  root_uuid = (
    "DRY-RUN-ROOT-UUID"
    if ctx.dry
    else subprocess.run(
      f"blkid --match-tag UUID --output value /dev/mapper/{ctx.host}",
      check=True,
      shell=True,
      capture_output=True,
      text=True,
    ).stdout.strip()
  )

  btrfs_mounts = [
    ("@", "/"),
    ("@snapshots", "/.snapshots"),
    ("@var_cache", "/var/cache"),
    ("@var_log", "/var/log"),
    ("@home", "/home"),
  ]

  fstab_entries = [
    *[f"UUID={root_uuid} {mount} btrfs compress=zstd,noatime,subvol={subvol} 0 0" for subvol, mount in btrfs_mounts],
    f"UUID={efi_uuid} /boot/efi vfat defaults,noatime 0 2",
    "tmpfs /tmp tmpfs defaults,noatime,mode=1777 0 0",
  ]

  write(fstab_entries, "/mnt/etc/fstab", ctx.dry)

  sudoers_entries = [
    'Defaults secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"',
    'Defaults env_keep += "SUDO_EDITOR EDITOR VISUAL"',
    "root ALL=(ALL:ALL) ALL",
    "%wheel ALL=(ALL:ALL) ALL",
    "@includedir /etc/sudoers.d",
  ]

  write(sudoers_entries, "/mnt/etc/sudoers", ctx.dry)

  defaults = load_defaults(ctx.distro_id)
  distro = get_distro(ctx.distro_id, ctx.dry)

  # fmt: off
  write([f"{ctx.host}"], "/mnt/etc/hostname", ctx.dry)
  write([f"127.0.0.1 localhost {ctx.host}", "::1 localhost"], "/mnt/etc/hosts", ctx.dry)
  write([f"server {str(server)}" for server in defaults["ntp"]], "/mnt/etc/ntpd.conf", ctx.dry)
  # fmt: on

  for path, lines in distro.locale_settings(ctx.config.locale, ctx.config.libc):
    write(lines, f"/mnt{path}", ctx.dry)

  for path, lines in distro.timezone_settings(ctx.config.keymap, ctx.config.timezone):
    write(lines, f"/mnt{path}", ctx.dry)

  if ctx.config.libc == "glibc":
    cmd(distro.reconfigure_locale(), ctx.dry)

  generate_chroot(
    "/mnt/root/chroot.sh",
    ctx,
    ctx.luks_pass or "",
    ctx.distro_name,
    ctx.dry,
    warnings,
  )

  cmd("cp /etc/resolv.conf /mnt/etc", ctx.dry)
  cmd("mount --types sysfs none /mnt/sys", ctx.dry)
  cmd("mount --types proc none /mnt/proc", ctx.dry)
  cmd("mount --rbind /run /mnt/run", ctx.dry)
  cmd("mount --rbind /dev /mnt/dev", ctx.dry)
  cmd("chroot /mnt /bin/bash -x /root/chroot.sh", ctx.dry)
  assert ctx.user_name is not None
  assert ctx.user_pass is not None
  scmd("chroot /mnt passwd root", f"{ctx.user_pass}\n{ctx.user_pass}\n", ctx.dry)
  scmd(f"chroot /mnt passwd {ctx.user_name}", f"{ctx.user_pass}\n{ctx.user_pass}\n", ctx.dry)


def step_05_cleanup(ctx: InstallerContext, _warnings: list[str]) -> None:
  cmd("rm -rf /mnt/root/chroot.sh", ctx.dry)
  cmd("umount --recursive /mnt", ctx.dry)


def get_install_steps(ctx: InstallerContext) -> list[Callable[[InstallerContext, list[str]], None]]:
  """Get installation steps, skipping bootstrap and config for generic distro."""
  all_steps = [
    step_01_settings,
    step_02_disk_setup,
    step_03_system_bootstrap,
    step_04_system_installation_and_configuration,
    step_05_cleanup,
  ]

  # Skip system bootstrap and configuration for generic distro
  if ctx.distro_id == "linux":
    return [
      step_01_settings,
      step_02_disk_setup,
      step_05_cleanup,
    ]

  return all_steps
