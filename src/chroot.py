import os
import subprocess
import json
from src.ansi_codes import gray, reset
from src.utils import info, error, detect_gpu_vendors, get_gpu_packages, print_detected_gpus
from src.context import InstallerContext
from textwrap import dedent


def _section_header() -> str:
  return dedent("""\
    #!/usr/bin/env -S bash -e
  """)


def _section_luks_key_setup(crypt_uuid: str, luks_pass: str) -> str:
  return dedent(f"""\
    mkdir -p /etc/dracut.conf.d
    dd if=/dev/urandom of=/boot/crypto.key bs=1024 count=4
    chmod 000 /boot/crypto.key

    tee /etc/dracut.conf.d/10-crypt.conf &> /dev/null << EOF
    install_items+=" /boot/crypto.key /etc/crypttab "
    EOF

    tee /etc/dracut.conf.d/20-modules.conf &> /dev/null << EOF
    add_dracutmodules+=" crypt btrfs resume "
    EOF

    cryptsetup luksAddKey /dev/disk/by-partlabel/ENCRYPTED /boot/crypto.key << EOF
    {luks_pass}
    EOF

    echo "ENCRYPTED UUID={crypt_uuid} /crypto.key luks,discard" >> /etc/crypttab
    chmod -R g-rwx,o-rwx /boot
  """)


def _section_grub_install(crypt_uuid: str, distro_name: str) -> str:
  return dedent(f"""\
    mount --types efivarfs none /sys/firmware/efi/efivars

    tee /etc/default/grub &> /dev/null << EOF
    GRUB_CMDLINE_LINUX_DEFAULT="quiet rd.auto=1 rd.luks.name={crypt_uuid}=ENCRYPTED rd.luks.allow-discards={crypt_uuid}"
    GRUB_CMDLINE_LINUX=""
    GRUB_DEFAULT=0
    GRUB_DISTRIBUTOR={distro_name}
    GRUB_ENABLE_CRYPTODISK=yes
    GRUB_TIMEOUT=10
    EOF

    grub-install --target=x86_64-efi --boot-directory=/boot --efi-directory=/boot/efi --bootloader-id={distro_name} --recheck
  """)


def _get_package_list(ctx: InstallerContext) -> list[str]:
  """Get final package list based on profile configuration and GPU detection."""
  config_file = os.path.join(os.path.dirname(__file__), "../config.json")
  try:
    with open(config_file) as f:
      config_data = json.load(f)
      if "packages" not in config_data or ctx.distro_id not in config_data["packages"]:
        error(f"No packages found for distro '{ctx.distro_id}' in config.json")
        return []
      default_pkgs: list[str] = config_data["packages"][ctx.distro_id]
  except (FileNotFoundError, json.JSONDecodeError) as e:
    error(f"Error loading packages from config.json: {e}")
    return []

  # Start with default packages
  final_pkgs: set[str] = set(default_pkgs)

  info("Detecting GPU hardware...")
  gpu_vendors = detect_gpu_vendors()
  print_detected_gpus(gpu_vendors)
  gpu_packages = get_gpu_packages(ctx.distro_id, gpu_vendors)
  if gpu_packages:
    info(f"Adding GPU packages: {', '.join(gpu_packages)}")
    final_pkgs.update(gpu_packages)

  # Apply profile package configuration if available
  if ctx.profile and ctx.profile.packages:
    profile_pkgs = ctx.profile.packages
    if profile_pkgs.additional:
      final_pkgs.update(profile_pkgs.additional)
    if profile_pkgs.exclude:
      final_pkgs.difference_update(profile_pkgs.exclude)

  return sorted(final_pkgs)


def _section_install_packages(ctx: InstallerContext) -> str:
  pkgs_list = _get_package_list(ctx)
  if not pkgs_list:
    return ""

  pkgs = " ".join(pkgs_list)
  return dedent(f"""\
    yes | xi && yes | xbps-install -USy --repository "{ctx.repository}" {pkgs}
  """)


def _section_post_install(ctx: InstallerContext) -> str:
  config = dedent("""\
    xbps-reconfigure --force --all
  """)
  services = dedent("""\
    ln -srf /etc/sv/{chronyd,dhcpcd,grub-btrfs,ufw} /var/service/
  """)
  firewall = dedent("""\
    ufw default deny incoming
    ufw default allow outgoing
  """)
  users = dedent(f"""\
    chsh --shell /bin/bash root
    useradd --create-home --groups wheel,users,input,audio,video,network --shell /bin/fish {ctx.user_name}
  """)
  config += services
  config += firewall
  config += users

  # Add profile-specific post-install commands
  if ctx.profile and ctx.profile.post_install_commands:
    profile_commands = "\n".join(ctx.profile.post_install_commands)
    config += f"\n{profile_commands}\n"

  return config


def generate_chroot(
  path: str,
  ctx: InstallerContext,
  luks_pass: str,
  distro_name: str,
  dry_run: bool = False,
) -> None:
  if dry_run:
    crypt_uuid = "MOCK-CRYPT-UUID"
  else:
    blkid = "blkid --match-tag UUID --output value"
    result = subprocess.run(
      f"{blkid} /dev/disk/by-partlabel/ENCRYPTED", check=True, shell=True, capture_output=True, text=True
    )
    crypt_uuid = result.stdout.strip()
  parts: list[str] = [
    _section_header(),
    _section_luks_key_setup(crypt_uuid, luks_pass),
    _section_grub_install(crypt_uuid, distro_name),
    _section_install_packages(ctx),
    _section_post_install(ctx),
  ]
  if dry_run:
    info(f"{gray}[DRY RUN] generated chroot script:{reset}")
    print("\n".join(parts))
  else:
    with open(path, "w") as f:
      _ = f.write("\n".join(parts))
    _ = os.chmod(path, 0o755)
