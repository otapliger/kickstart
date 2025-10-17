import subprocess
import sys
import os
from src.ansi_codes import bold, yellow, reset
from src.chroot import generate_chroot
from src.utils import (
  error,
  info,
  cmd,
  write,
  set_disk,
  set_host,
  set_luks,
  set_pass,
  set_user,
)


def step_01_settings(ctx):
  ctx.host = set_host()
  ctx.disk = set_disk()
  ctx.luks_pass = set_luks()
  ctx.user_name = set_user()
  ctx.user_pass = set_pass(ctx.user_name)
  warning = f"{bold}{yellow}WARNING:{reset}"
  response = input(f"{warning} All data on {ctx.disk} will be erased. Are you sure you want to continue? [y/N]: ")
  if response.lower() not in ("y", "yes"):
    error("Installation aborted. No changes were made to the system.")
    sys.exit(0)
  print()
  ctx.cryptroot = "/dev/disk/by-partlabel/ENCRYPTED"
  ctx.esp = "/dev/disk/by-partlabel/ESP"
  ctx.root = f"/dev/mapper/{ctx.host}"


def step_02_wipe_disk(ctx):
  info("- wiping {}".format(ctx.disk))
  cmd(f"wipefs -af {ctx.disk}", ctx.args.dry)
  cmd(f"sgdisk -Zo {ctx.disk}", ctx.args.dry)


def step_03_partition_disk(ctx):
  info("- creating new partitions on {}".format(ctx.disk))
  esp = "mkpart ESP fat32 1MiB 513MiB"
  encrypted = "mkpart ENCRYPTED 513MiB 100%"
  cmd(f"parted -s {ctx.disk} mklabel gpt {esp} {encrypted} set 1 esp on", ctx.args.dry)


def step_04_kernel_notify(ctx):
  info("- informing the Kernel about the disk changes")
  cmd(f"partprobe {ctx.disk}", ctx.args.dry)


def step_05_format_esp(ctx):
  info("- formatting the EFI Partition as FAT32")
  cmd(f"mkfs.vfat -F32 -n ESP {ctx.esp}", ctx.args.dry)


def step_06_setup_luks(ctx):
  info("- creating LUKS Container for the root partition")
  cryptsetup = f"echo -n '{ctx.luks_pass}' | cryptsetup"
  cmd(f"{cryptsetup} luksFormat --type luks1 --pbkdf-force-iterations 1000 {ctx.cryptroot} -d -", ctx.args.dry)
  cmd(f"{cryptsetup} luksOpen {ctx.cryptroot} {ctx.host} -d -", ctx.args.dry)


def step_07_format_btrfs(ctx):
  info("- formatting the LUKS container as BTRFS")
  cmd(f"mkfs.btrfs -L {ctx.host} {ctx.root}", ctx.args.dry)
  cmd(f"mount -o compress=zstd,noatime {ctx.root} /mnt", ctx.args.dry)


def step_08_create_subvols(ctx):
  info("- creating BTRFS subvolumes")
  subvols = ["", "home", "snapshots", "var_cache", "var_log"]
  for sub in subvols:
    name = f"/mnt/@{sub}" if sub else "/mnt/@"
    cmd(f"btrfs subvolume create {name}", ctx.args.dry)
  cmd("umount /mnt", ctx.args.dry)


def step_09_mount_subvols(ctx):
  info("- mounting the newly created subvolumes")
  mount = "mount -o X-mount.mkdir,compress=zstd,noatime,subvol=@"
  cmd(f"{mount} {ctx.root} /mnt", ctx.args.dry)
  cmd(f"{mount}snapshots {ctx.root} /mnt/.snapshots", ctx.args.dry)
  cmd(f"{mount}var_cache {ctx.root} /mnt/var/cache", ctx.args.dry)
  cmd(f"{mount}var_log {ctx.root} /mnt/var/log", ctx.args.dry)
  cmd(f"{mount}home {ctx.root} /mnt/home", ctx.args.dry)


def step_10_mount_efi(ctx):
  cmd("mkdir -p /mnt/boot/efi", ctx.args.dry)
  cmd(f"mount {ctx.esp} /mnt/boot/efi", ctx.args.dry)


def step_11_setup_xbps(ctx):
  cmd("mkdir -p /mnt/var/db/xbps/keys", ctx.args.dry)
  cmd("cp /var/db/xbps/keys/* /mnt/var/db/xbps/keys", ctx.args.dry)


def step_12_install_base(ctx):
  info("- installing the base system (it may take a few minutes)")
  path = os.path.join(os.path.dirname(__file__), "../pkgs/base.void")
  with open(path) as f:
    pkgs = " ".join(line.strip() for line in f if line.strip())
    cmd(f"xbps-install -Sy -R '{ctx.args.repository}' -r /mnt {pkgs}", ctx.args.dry)


def step_13_etc_bootstrap(ctx):
  if ctx.args.dry:
    efi_uuid = "DRY-RUN-EFI-UUID"
    root_uuid = "DRY-RUN-ROOT-UUID"
  else:
    blkid = "blkid --match-tag UUID --output value"
    efi_uuid = subprocess.run(f"{blkid} /dev/disk/by-partlabel/ESP", check=True, shell=True)
    root_uuid = subprocess.run(f"{blkid} /dev/mapper/{ctx.host}", check=True, shell=True)
  write(
    "/mnt/etc/fstab",
    [
      f"UUID={root_uuid} / btrfs compress=zstd,noatime,subvol=@ 0 0",
      f"UUID={root_uuid} /.snapshots btrfs compress=zstd,noatime,subvol=@snapshots 0 0",
      f"UUID={root_uuid} /var/cache btrfs compress=zstd,noatime,subvol=@var_cache 0 0",
      f"UUID={root_uuid} /var/log btrfs compress=zstd,noatime,subvol=@var_log 0 0",
      f"UUID={root_uuid} /home btrfs compress=zstd,noatime,subvol=@home 0 0",
      f"UUID={efi_uuid} /boot/efi vfat defaults,noatime 0 2",
      "tmpfs /tmp tmpfs defaults,noatime,mode=1777 0 0",
    ],
  )
  write(
    "/mnt/etc/sudoers",
    [
      'Defaults secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"',
      'Defaults env_keep += "SUDO_EDITOR EDITOR VISUAL"',
      "root ALL=(ALL:ALL) ALL",
      "%wheel ALL=(ALL:ALL) ALL",
      "@includedir /etc/sudoers.d",
    ],
  )
  write("/mnt/etc/hostname", [f"{ctx.host}"])
  write("/mnt/etc/hosts", [f"127.0.0.1 localhost {ctx.host}", "::1 localhost"])
  write("/mnt/etc/ntpd.conf", [f"server {i}.fi.pool.ntp.org" for i in range(4)])
  write("/mnt/etc/locale.conf", [f"export {var}={ctx.args.locale}" for var in ["LANG", "LANGUAGE", "LC_ALL"]])
  write("/mnt/etc/rc.conf", [f'TIMEZONE="{ctx.args.timezone}"', 'HARDWARECLOCK="UTC"', f'KEYMAP="{ctx.args.keymap}"'])
  if ctx.args.libc == "glibc":
    write("/mnt/etc/default/libc-locales", [f"{ctx.args.locale}"])
    cmd("xbps-reconfigure -f glibc-locales -r /mnt", ctx.args.dry)


def step_14_chroot_setup(ctx):
  info("- setting up the system (settings, packages and users)")
  generate_chroot(
    path="/mnt/root/chroot.sh",
    hostname=ctx.host,
    username=ctx.user_name,
    luks_pass=ctx.luks_pass,
    btrfs_opts="compress=zstd,noatime",
    distro_name="Void",
    repository=ctx.args.repository,
    dry_run=ctx.args.dry,
  )
  cmd("cp /etc/resolv.conf /mnt/etc", ctx.args.dry)
  cmd("mount --types sysfs none /mnt/sys", ctx.args.dry)
  cmd("mount --types proc none /mnt/proc", ctx.args.dry)
  cmd("mount --rbind /run /mnt/run", ctx.args.dry)
  cmd("mount --rbind /dev /mnt/dev", ctx.args.dry)
  cmd("mount --types efivarfs none /sys/firmware/efi/efivars", ctx.args.dry)
  cmd("chroot /mnt /bin/bash -x /root/chroot.sh", ctx.args.dry)
  cmd(f"yes '{ctx.user_pass}' | chroot /mnt passwd root", ctx.args.dry)
  cmd(f"yes '{ctx.user_pass}' | chroot /mnt passwd {ctx.user_name}", ctx.args.dry)


def step_15_cleanup(ctx):
  cmd("rm -rf /mnt/root/chroot.sh", ctx.args.dry)
  cmd("umount --recursive /mnt", ctx.args.dry)
  print()
  info("Installation completed. You can now reboot your system.")


install = [
  step_01_settings,
  step_02_wipe_disk,
  step_03_partition_disk,
  step_04_kernel_notify,
  step_05_format_esp,
  step_06_setup_luks,
  step_07_format_btrfs,
  step_08_create_subvols,
  step_09_mount_subvols,
  step_10_mount_efi,
  step_11_setup_xbps,
  step_12_install_base,
  step_13_etc_bootstrap,
  step_14_chroot_setup,
  step_15_cleanup,
]
