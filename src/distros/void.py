"""Void Linux specific commands and configurations"""

import json
from textwrap import dedent
from src.utils import get_resource_path


def _load_void_defaults() -> dict[str, str]:
  """Load Void Linux defaults from config.json"""
  config_file = get_resource_path("config.json")
  with open(config_file) as f:
    config_data = json.load(f)
    return config_data["defaults"]["void"]


def prepare_base_system() -> list[str]:
  return [
    "mkdir -p /mnt/var/db/xbps/keys",
    "cp /var/db/xbps/keys/* /mnt/var/db/xbps/keys",
  ]


def install_base_system(packages: list[str], repository: str | None = None) -> str:
  pkgs = " ".join(packages)
  repo = repository or _load_void_defaults()["repository"]
  return f"xbps-install -Sy -R '{repo}' -r /mnt {pkgs}"


def install_packages(packages: list[str], repository: str | None = None) -> str:
  pkgs = " ".join(packages)
  repo = repository or _load_void_defaults()["repository"]
  return dedent(f"""\
    yes | xbps-install -USy --repository "{repo}" {pkgs}
  """)


def reconfigure_system() -> str:
  return "xbps-reconfigure --force --all"


def reconfigure_locale() -> str:
  return "xbps-reconfigure -f glibc-locales -r /mnt"


def enable_services(services: list[str]) -> str:
  service_list = ",".join(services)
  return f"ln -srf /etc/sv/{{{service_list}}} /var/service/"


def locale_settings(locale: str, libc: str | None = None) -> list[tuple[str, list[str]]]:
  files = [
    ("/etc/locale.conf", [f"export {var}={locale}" for var in ["LANG", "LANGUAGE", "LC_ALL"]]),
  ]

  if (libc or _load_void_defaults()["libc"]) == "glibc":
    files.append(("/etc/default/libc-locales", [locale]))

  return files


def timezone_settings(keymap: str, timezone: str | None = None) -> list[tuple[str, list[str]]]:
  return [
    (
      "/etc/rc.conf",
      [
        f'TIMEZONE="{timezone or _load_void_defaults()["timezone"]}"',
        'HARDWARECLOCK="UTC"',
        f'KEYMAP="{keymap}"',
      ],
    ),
  ]


def initramfs_config(crypt_uuid: str, luks_pass: str) -> str:
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

    echo "ENCRYPTED UUID={crypt_uuid} /boot/crypto.key luks,discard" >> /etc/crypttab
    chmod -R g-rwx,o-rwx /boot
  """)


def base_packages() -> list[str]:
  return [
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


def default_services() -> list[str]:
  return ["chronyd", "dhcpcd", "grub-btrfs", "ufw"]
