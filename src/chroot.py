import os
import subprocess
import json
from src.ansi_codes import gray, reset
from src.utils import info, error
from textwrap import dedent


def section_header() -> str:
  return dedent("""\
    #!/usr/bin/env -S bash -e
  """)


def section_grub_install(crypt_uuid: str, distro_name: str) -> str:
  return dedent(f"""\
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


def section_install_packages(repository: str) -> str:
  pkgs_file = os.path.join(os.path.dirname(__file__), "../config/void/pkgs.json")
  try:
    with open(pkgs_file) as f:
      pkgs_list = json.load(f)
      pkgs = " ".join(pkgs_list)
  except (FileNotFoundError, json.JSONDecodeError) as e:
    error(f"Error loading packages from pkgs.json: {e}")
    return ""
  return dedent(f"""\
    yes | xi && yes | xbps-install -USy --repository "{repository}" {pkgs}
  """)


def section_third_party_packages() -> str:
  opt = dedent("""\
    mkdir -p /opt
  """)
  neovim = dedent("""\
    TMP_NVIM=$(mktemp)
    curl -sSLo "${TMP_NVIM}" https://github.com/neovim/neovim/releases/download/nightly/nvim-linux-x86_64.tar.gz
    tar -C /opt -xzf "${TMP_NVIM}" && mv /opt/nvim-linux-x86_64 /opt/nvim-nightly && ln -sf /opt/nvim-nightly/bin/nvim /usr/bin/nvim && rm -rf "${TMP_NVIM}"
  """)
  opt += neovim
  return opt


def section_post_install(username: str) -> str:
  config = dedent("""\
    xbps-reconfigure --force --all
  """)
  services = dedent("""\
    ln -srf /etc/sv/{dbus,elogind,grub-btrfs,NetworkManager,openntpd,ufw} /var/service/
  """)
  firewall = dedent("""\
    ufw default deny incoming
    ufw default allow outgoing
  """)
  audio = dedent("""\
    mkdir -p /etc/pipewire/pipewire.conf.d
    ln -s /usr/share/examples/wireplumber/10-wireplumber.conf /etc/pipewire/pipewire.conf.d/
    ln -s /usr/share/examples/pipewire/20-pipewire-pulse.conf /etc/pipewire/pipewire.conf.d/
  """)
  users = dedent(f"""\
    chsh --shell /bin/bash root
    useradd --create-home --groups wheel,users,input,audio,video,network --shell /bin/fish {username}
  """)
  config += services
  config += firewall
  config += audio
  config += users
  return config


def generate_chroot(
  path: str,
  username: str,
  distro_name: str,
  repository: str,
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
    section_header(),
    section_grub_install(crypt_uuid, distro_name),
    section_install_packages(repository),
    section_third_party_packages(),
    section_post_install(username),
  ]
  if dry_run:
    info(f"{gray}[DRY RUN] generated chroot script:{reset}")
    print("\n".join(parts))
  else:
    with open(path, "w") as f:
      f.write("\n".join(parts))
    os.chmod(path, 0o755)
