"""Arch Linux specific commands and configurations"""

from textwrap import dedent


def prepare_base_system() -> list[str]:
  return []


# Arch uses mirrors from /etc/pacman.d/mirrorlist
# pacstrap doesn't support setting the repository URL directly
# so repository parameter is ignored
def install_base_system(packages: list[str], _repository: str | None = None) -> str:
  pkgs = " ".join(packages)
  return f"pacstrap /mnt {pkgs}"


# Arch uses mirrors from /etc/pacman.d/mirrorlist
# pacstrap doesn't support setting the repository URL directly
# so repository parameter is ignored
def install_packages(packages: list[str], _repository: str | None = None) -> str:
  pkgs = " ".join(packages)
  return f"pacman -Syu --noconfirm {pkgs}"


def reconfigure_system() -> str:
  return ""


def reconfigure_locale() -> str:
  return "arch-chroot /mnt locale-gen"


def enable_services(services: list[str]) -> str:
  return "\n".join(f"systemctl enable {svc}" for svc in services)


# Arch supports only glibc, so libc parameter is ignored
def locale_settings(locale: str, _libc: str | None = None) -> list[tuple[str, list[str]]]:
  return [
    ("/etc/locale.conf", [f"{var}={locale}" for var in ["LANG", "LANGUAGE", "LC_ALL"]]),
    ("/etc/locale.gen", [f"{locale} UTF-8"]),
  ]


def setup_commands(props: dict[str, str]) -> list[str]:
  timezone = props.get("timezone", "UTC")
  keymap = props.get("keymap", "us")
  return [
    f"ln -sf /usr/share/zoneinfo/{timezone} /etc/localtime",
    f"echo 'KEYMAP={keymap}' > /etc/vconsole.conf",
  ]


def initramfs_config(crypt_uuid: str, luks_pass: str) -> str:
  return dedent(f"""\
    mkdir -p /etc
    dd if=/dev/urandom of=/boot/crypto.key bs=1024 count=4
    chmod 000 /boot/crypto.key

    cryptsetup luksAddKey /dev/disk/by-partlabel/ENCRYPTED /boot/crypto.key << EOF
    {luks_pass}
    EOF

    echo "ENCRYPTED UUID={crypt_uuid} /boot/crypto.key luks,discard" >> /etc/crypttab
    chmod -R g-rwx,o-rwx /boot

    sed -i '/^FILES=/c\\FILES=(/boot/crypto.key /etc/crypttab)' /etc/mkinitcpio.conf
    sed -i '/^HOOKS=/c\\HOOKS=(base udev autodetect keyboard modconf block encrypt btrfs filesystems fsck)' /etc/mkinitcpio.conf

    # Append lines if sed didn't find them (they may not exist in default mkinitcpio.conf)
    grep -q '^FILES=' /etc/mkinitcpio.conf || echo 'FILES=(/boot/crypto.key /etc/crypttab)' >> /etc/mkinitcpio.conf
    grep -q '^HOOKS=' /etc/mkinitcpio.conf || echo 'HOOKS=(base udev autodetect keyboard modconf block encrypt btrfs filesystems fsck)' >> /etc/mkinitcpio.conf

    mkinitcpio -P
  """)


def base_packages() -> list[str]:
  return [
    "base",
    "base-devel",
    "chrony",
    "cryptsetup",
    "dhcpcd",
    "efibootmgr",
    "grub",
    "grub-btrfs",
    "linux",
    "ufw",
  ]


def default_services() -> list[str]:
  return ["chronyd", "dhcpcd", "ufw"]
