import os
import subprocess
import json
from rich.console import Console
from src.utils import get_gpu_packages, get_resource_path
from src.context import InstallerContext
from src.distros import get_distro
from src.tui import TUI
from textwrap import dedent

console = Console()


def _section_header() -> str:
  return dedent("""\
    #!/usr/bin/env -S bash -e
  """)


def _section_luks_key_setup(crypt_uuid: str, luks_pass: str, distro_id: str, dry_mode: bool) -> str:
  distro = get_distro(distro_id, dry_mode)
  return distro.initramfs_config(crypt_uuid, luks_pass)


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


def _get_package_list(ctx: InstallerContext, warnings: list[str]) -> list[str]:
  """Get final package list based on profile configuration and GPU detection."""
  config_file = get_resource_path("config.json")
  with open(config_file) as f:
    config_data = json.load(f)
    if "packages" not in config_data or ctx.distro_id not in config_data["packages"]:
      return []
    default_pkgs: list[str] = config_data["packages"][ctx.distro_id]

  gpu_packages = get_gpu_packages(ctx.distro_id, warnings if ctx.dry else None)
  profile_pkgs = ctx.profile.packages if ctx.profile else None

  # fmt: off
  final_pkgs = (
    set(default_pkgs)
    | set(gpu_packages)
    | (set(profile_pkgs.additional) if profile_pkgs else set())
  ) - (set(profile_pkgs.exclude) if profile_pkgs else set())
  # fmt: on

  return sorted(final_pkgs)


def _section_install_packages(ctx: InstallerContext, warnings: list[str]) -> str:
  pkgs_list = _get_package_list(ctx, warnings)
  if not pkgs_list:
    return ""

  distro = get_distro(ctx.distro_id, ctx.dry)
  return distro.install_packages(pkgs_list, ctx.repository)


def _section_post_install(ctx: InstallerContext) -> str:
  commands = []
  distro = get_distro(ctx.distro_id, ctx.dry)

  reconfigure_cmd = distro.reconfigure_system()
  if reconfigure_cmd:
    commands.append(f"{reconfigure_cmd}\n")

  services = distro.default_services()
  if services:
    commands.append(f"{distro.enable_services(services)}\n")

  commands.append(
    dedent("""\
      ufw default deny incoming
      ufw default allow outgoing
    """)
  )

  commands.append(
    dedent(f"""\
      chsh --shell /bin/bash root
      useradd --create-home --groups wheel,users,input,audio,video,network --shell /bin/fish {ctx.user_name}
    """)
  )

  if ctx.profile and ctx.profile.post_install_commands:
    profile_commands = "\n".join(ctx.profile.post_install_commands)
    commands.append(f"\n{profile_commands}\n")

  return "".join(commands)


def generate_chroot(
  path: str,
  ctx: InstallerContext,
  luks_pass: str,
  distro_name: str,
  dry_run: bool,
  warnings: list[str],
  ui: TUI,
) -> None:
  crypt_uuid = (
    "MOCK-CRYPT-UUID"
    if dry_run
    else subprocess.run(
      "blkid --match-tag UUID --output value /dev/disk/by-partlabel/ENCRYPTED",
      check=True,
      shell=True,
      capture_output=True,
      text=True,
    ).stdout.strip()
  )
  parts: list[str] = [
    _section_header(),
    _section_luks_key_setup(crypt_uuid, luks_pass, ctx.distro_id, ctx.dry),
    _section_grub_install(crypt_uuid, distro_name),
    _section_install_packages(ctx, warnings),
    _section_post_install(ctx),
  ]
  if dry_run:
    ui.print("[bold green][dim][DRY RUN] Generated chroot script:[/][/]")
    ui.print(f"[bold green][dim]{'\n'.join(parts)}[/][/]")
  else:
    with open(path, "w") as f:
      _ = f.write("\n".join(parts))
    _ = os.chmod(path, 0o755)
