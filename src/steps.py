import subprocess
import sys
from typing import Callable
from src.ansi_codes import bold, yellow, reset
from src.context import InstallerContext
from src.chroot import generate_chroot
from src.utils import (
  error,
  info,
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


def step_01_settings(ctx: InstallerContext) -> None:
  DEFAULTS = load_defaults(ctx.distro_id)

  print(f"  • C library: {ctx.config.libc}")
  print(f"  • Keymap: {ctx.config.keymap}")
  print(f"  • Locale: {ctx.config.locale}")
  print(f"  • Timezone: {ctx.config.timezone}")
  print()

  if ctx.config.hostname:
    ctx.host = ctx.config.hostname

  elif ctx.profile and ctx.profile.hostname:
    ctx.host = ctx.profile.hostname

  else:
    ctx.host = set_host(ctx.distro_id)

  ctx.disk = set_disk()
  ctx.luks_pass = set_luks()

  # User creation
  ctx.user_name = set_user()
  ctx.user_pass = set_pass(ctx.user_name)

  # Repository selection with profile override
  profile_repo = ctx.profile.config.repository if ctx.profile else None
  if profile_repo:
    ctx.repository = profile_repo
    print(f"Using repository from profile: {ctx.repository}")

  elif ctx.config.repository != DEFAULTS["repository"]:
    ctx.repository = ctx.config.repository
    print(f"Using repository from command line: {ctx.repository}")

  else:
    ctx.repository = set_mirror(ctx.distro_id)

  # Confirmation prompt
  warning = f"{bold}{yellow}WARNING:{reset}"
  response = input(f"{warning} All data on {ctx.disk} will be erased. Are you sure you want to continue? [y/N]: ")
  if response.lower() not in ("y", "yes"):
    error("Installation aborted. No changes were made to the system.")
    sys.exit(0)

  print()

  ctx.cryptroot = "/dev/disk/by-partlabel/ENCRYPTED"
  ctx.esp = "/dev/disk/by-partlabel/ESP"
  ctx.root = f"/dev/mapper/{ctx.host}"


def step_02_disk_setup(ctx: InstallerContext) -> None:
  info("- wiping disk {}".format(ctx.disk))
  cmd(f"wipefs -af {ctx.disk}", ctx.dry)
  cmd(f"sgdisk -Zo {ctx.disk}", ctx.dry)

  info("- creating partitions")
  cmd(f"parted -s {ctx.disk} mklabel gpt", ctx.dry)
  cmd(f"parted -s {ctx.disk} mkpart ESP fat32 1MiB 513MiB", ctx.dry)
  cmd(f"parted -s {ctx.disk} mkpart ENCRYPTED 513MiB 100%", ctx.dry)
  cmd(f"parted -s {ctx.disk} set 1 esp on", ctx.dry)

  info("- updating kernel partition table")
  cmd(f"partprobe {ctx.disk}", ctx.dry)

  info("- formatting EFI partition")
  cmd(f"mkfs.vfat -F32 -n ESP {ctx.esp}", ctx.dry)

  info("- setting up disk encryption")
  # At this point we should always have a LUKS password
  assert isinstance(ctx.luks_pass, str), "luks_pass must be set before disk setup"
  scmd(f"cryptsetup luksFormat --type luks1 --pbkdf-force-iterations 1000 {ctx.cryptroot} -d -", ctx.luks_pass, ctx.dry)
  scmd(f"cryptsetup luksOpen {ctx.cryptroot} {ctx.host} -d -", ctx.luks_pass, ctx.dry)

  info("- creating BTRFS filesystem")
  cmd(f"mkfs.btrfs -L {ctx.host} {ctx.root}", ctx.dry)
  cmd(f"mount -o compress=zstd,noatime {ctx.root} /mnt", ctx.dry)

  info("- creating subvolumes")
  subvols = ["", "home", "snapshots", "var_cache", "var_log"]
  for sub in subvols:
    name = f"/mnt/@{sub}" if sub else "/mnt/@"
    cmd(f"btrfs subvolume create {name}", ctx.dry)
  cmd("umount /mnt", ctx.dry)

  info("- mounting filesystem")
  mount = "mount -o X-mount.mkdir,compress=zstd,noatime,subvol=@"
  cmd(f"{mount} {ctx.root} /mnt", ctx.dry)
  cmd(f"{mount}snapshots {ctx.root} /mnt/.snapshots", ctx.dry)
  cmd(f"{mount}var_cache {ctx.root} /mnt/var/cache", ctx.dry)
  cmd(f"{mount}var_log {ctx.root} /mnt/var/log", ctx.dry)
  cmd(f"{mount}home {ctx.root} /mnt/home", ctx.dry)
  cmd("mkdir -p /mnt/boot/efi", ctx.dry)
  cmd(f"mount {ctx.esp} /mnt/boot/efi", ctx.dry)


def step_03_system_bootstrap(ctx: InstallerContext) -> None:
  info("- configuring package manager")
  cmd("mkdir -p /mnt/var/db/xbps/keys", ctx.dry)
  cmd("cp /var/db/xbps/keys/* /mnt/var/db/xbps/keys", ctx.dry)

  info("- installing base system")
  pkgs_list = [
    "base-devel",
    "base-system",
    "chrony",
    "cryptsetup",
    "dhcpcd",
    "efibootmgr",
    "grub-btrfs",
    "grub-x86_64-efi",
    "linux",
    "ufw",
    "void-repo-nonfree",
  ]

  pkgs = " ".join(pkgs_list)
  defaults = load_defaults(ctx.distro_id)
  repository = ctx.repository or defaults["repository"]
  cmd(f"xbps-install -Sy -R '{repository}' -r /mnt {pkgs}", ctx.dry)


def step_04_system_installation_and_configuration(ctx: InstallerContext) -> None:
  info("- configuring system files")
  if ctx.dry:
    efi_uuid = "DRY-RUN-EFI-UUID"
    root_uuid = "DRY-RUN-ROOT-UUID"

  else:
    blkid = "blkid --match-tag UUID --output value"

    efi_uuid = subprocess.run(
      f"{blkid} /dev/disk/by-partlabel/ESP", check=True, shell=True, capture_output=True, text=True
    ).stdout.strip()

    root_uuid = subprocess.run(
      f"{blkid} /dev/mapper/{ctx.host}", check=True, shell=True, capture_output=True, text=True
    ).stdout.strip()

  write(
    [
      f"UUID={root_uuid} / btrfs compress=zstd,noatime,subvol=@ 0 0",
      f"UUID={root_uuid} /.snapshots btrfs compress=zstd,noatime,subvol=@snapshots 0 0",
      f"UUID={root_uuid} /var/cache btrfs compress=zstd,noatime,subvol=@var_cache 0 0",
      f"UUID={root_uuid} /var/log btrfs compress=zstd,noatime,subvol=@var_log 0 0",
      f"UUID={root_uuid} /home btrfs compress=zstd,noatime,subvol=@home 0 0",
      f"UUID={efi_uuid} /boot/efi vfat defaults,noatime 0 2",
      "tmpfs /tmp tmpfs defaults,noatime,mode=1777 0 0",
    ],
    "/mnt/etc/fstab",
    ctx.dry,
  )

  write(
    [
      'Defaults secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"',
      'Defaults env_keep += "SUDO_EDITOR EDITOR VISUAL"',
      "root ALL=(ALL:ALL) ALL",
      "%wheel ALL=(ALL:ALL) ALL",
      "@includedir /etc/sudoers.d",
    ],
    "/mnt/etc/sudoers",
    ctx.dry,
  )

  defaults = load_defaults(ctx.distro_id)

  write([f"{ctx.host}"], "/mnt/etc/hostname", ctx.dry)
  write([f"127.0.0.1 localhost {ctx.host}", "::1 localhost"], "/mnt/etc/hosts", ctx.dry)
  write([f"server {str(server)}" for server in defaults["ntp"]], "/mnt/etc/ntpd.conf", ctx.dry)

  write(
    [f"export {var}={ctx.config.locale}" for var in ["LANG", "LANGUAGE", "LC_ALL"]], "/mnt/etc/locale.conf", ctx.dry
  )

  write(
    [f'TIMEZONE="{ctx.config.timezone}"', 'HARDWARECLOCK="UTC"', f'KEYMAP="{ctx.config.keymap}"'],
    "/mnt/etc/rc.conf",
    ctx.dry,
  )

  if ctx.config.libc == "glibc":
    write([f"{ctx.config.locale}"], "/mnt/etc/default/libc-locales", ctx.dry)
    cmd("xbps-reconfigure -f glibc-locales -r /mnt", ctx.dry)

  info("- installing packages and configuring services")

  generate_chroot(
    path="/mnt/root/chroot.sh",
    ctx=ctx,
    luks_pass=ctx.luks_pass or "",
    distro_name=ctx.distro_name,
    dry_run=ctx.dry,
  )

  cmd("cp /etc/resolv.conf /mnt/etc", ctx.dry)
  cmd("mount --types sysfs none /mnt/sys", ctx.dry)
  cmd("mount --types proc none /mnt/proc", ctx.dry)
  cmd("mount --rbind /run /mnt/run", ctx.dry)
  cmd("mount --rbind /dev /mnt/dev", ctx.dry)
  cmd("chroot /mnt /bin/bash -x /root/chroot.sh", ctx.dry)
  assert isinstance(ctx.user_name, str), "user_name must be set before configuring system"
  assert isinstance(ctx.user_pass, str), "user_pass must be set before configuring system"
  scmd("chroot /mnt passwd root", f"{ctx.user_pass}\n{ctx.user_pass}\n", ctx.dry)
  scmd(f"chroot /mnt passwd {ctx.user_name}", f"{ctx.user_pass}\n{ctx.user_pass}\n", ctx.dry)


def step_05_cleanup(ctx: InstallerContext) -> None:
  info("- finalizing installation")
  cmd("rm -rf /mnt/root/chroot.sh", ctx.dry)
  cmd("umount --recursive /mnt", ctx.dry)

  print()
  info("Installation completed. You can now reboot your system.")


install: list[Callable[[InstallerContext], None]] = [
  step_01_settings,
  step_02_disk_setup,
  step_03_system_bootstrap,
  step_04_system_installation_and_configuration,
  step_05_cleanup,
]
