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
    mkdir -p /etc/dracut.conf.d /etc/pacman.d/hooks
    dd if=/dev/urandom of=/boot/crypto.key bs=1024 count=4
    chmod 000 /boot/crypto.key

    tee /etc/dracut.conf.d/10-crypt.conf &> /dev/null << EOF
    install_items+=" /boot/crypto.key /etc/crypttab "
    EOF

    tee /etc/dracut.conf.d/20-modules.conf &> /dev/null << EOF
    add_dracutmodules+=" crypt btrfs resume "
    EOF

    # Disable mkinitcpio pacman hooks to prevent conflicts with dracut
    ln -sf /dev/null /etc/pacman.d/hooks/90-mkinitcpio-install.hook
    ln -sf /dev/null /etc/pacman.d/hooks/60-mkinitcpio-remove.hook

    cryptsetup luksAddKey /dev/disk/by-partlabel/ENCRYPTED /boot/crypto.key << EOF
    {luks_pass}
    EOF

    echo "ENCRYPTED UUID={crypt_uuid} /boot/crypto.key luks,discard" >> /etc/crypttab
    chmod -R g-rwx,o-rwx /boot

    dracut -f --omit i18n /boot/initramfs-linux.img
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
    "base",
    "base-devel",
    "chrony",
    "cryptsetup",
    "dhcpcd",
    "dracut",
    "efibootmgr",
    "grub",
    "grub-btrfs",
    "linux",
    "ufw",
  ]


def default_services() -> list[str]:
  return ["chronyd", "dhcpcd", "ufw"]
