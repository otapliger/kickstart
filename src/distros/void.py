"""Void Linux specific commands and configurations"""

from textwrap import dedent


def prepare_base_system() -> list[str]:
  return [
    "mkdir -p /mnt/var/db/xbps/keys",
    "cp /var/db/xbps/keys/* /mnt/var/db/xbps/keys",
  ]


def install_base_system(packages: list[str]) -> str:
  pkgs = " ".join(packages)
  return f"xbps-install -Sy -R https://repo-default.voidlinux.org/current -r /mnt {pkgs}"


def install_packages(packages: list[str]) -> str:
  pkgs = " ".join(packages)
  return dedent(f"""\
    yes | xbps-install -USy -R https://repo-default.voidlinux.org/current {pkgs}
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
    ("/etc/locale.conf", [f"{var}={locale}" for var in ["LANG", "LANGUAGE", "LC_ALL"]]),
  ]

  if libc == "glibc":
    files.append(("/etc/default/libc-locales", [f"{locale} UTF-8"]))

  return files


def setup_commands(props: dict[str, str]) -> list[str]:
  timezone = props.get("timezone", "UTC")
  keymap = props.get("keymap", "us")
  return [
    f"echo 'TIMEZONE=\"{timezone}\"' > /etc/rc.conf",
    "echo 'HARDWARECLOCK=\"UTC\"' >> /etc/rc.conf",
    f"echo 'KEYMAP=\"{keymap}\"' >> /etc/rc.conf",
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


def bootloader_config(crypt_uuid: str, distro_name: str) -> str:
  return dedent(f"""\
    mount --types efivarfs none /sys/firmware/efi/efivars

    tee /etc/default/grub &> /dev/null << EOF
    GRUB_CMDLINE_LINUX_DEFAULT="quiet rootflags=subvol=@ rd.auto=1 rd.luks.name={crypt_uuid}=ENCRYPTED rd.luks.allow-discards={crypt_uuid}"
    GRUB_CMDLINE_LINUX=""
    GRUB_DEFAULT=0
    GRUB_DISTRIBUTOR={distro_name}
    GRUB_ENABLE_CRYPTODISK=yes
    GRUB_TIMEOUT=10
    EOF

    grub-install --target=x86_64-efi --boot-directory=/boot --efi-directory=/boot/efi --bootloader-id={distro_name} --recheck
    grub-mkconfig -o /boot/grub/grub.cfg
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
