"""Generic Linux distro module for dry mode."""


def prepare_base_system() -> list[str]:
  return []


def install_base_system(packages: list[str]) -> str:
  pkgs = " ".join(packages)
  return f"{pkgs}"


def install_packages(packages: list[str]) -> str:
  pkgs = " ".join(packages)
  return f"{pkgs}"


def reconfigure_system() -> str:
  return ""


def reconfigure_locale() -> str:
  return ""


def enable_services(services: list[str]) -> str:
  srv = " ".join(services)
  return f"{srv}"


def locale_settings(_locale: str, _libc: str | None = None) -> list[tuple[str, list[str]]]:
  return []


def setup_commands(_props: dict[str, str]) -> list[str]:
  return []


def initramfs_config(_crypt_uuid: str, _luks_pass: str) -> str:
  return ""


def bootloader_config(_crypt_uuid: str, _distro_name: str) -> str:
  return ""


def base_packages() -> list[str]:
  return []


def default_services() -> list[str]:
  return []
