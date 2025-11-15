"""Generic Linux distro module for dry mode."""


def prepare_base_system() -> list[str]:
  return []


def install_base_system(_packages: list[str]) -> str:
  return ""


def install_packages(_packages: list[str]) -> str:
  return ""


def reconfigure_system() -> str:
  return ""


def reconfigure_locale() -> str:
  return ""


def enable_services(_services: list[str]) -> str:
  return ""


def locale_settings(_locale: str, _libc: str | None = None) -> list[tuple[str, list[str]]]:
  return []


def setup_commands(_props: dict[str, str]) -> list[str]:
  return []


def initramfs_config(_crypt_uuid: str, _luks_pass: str) -> str:
  return ""


def base_packages() -> list[str]:
  return []


def default_services() -> list[str]:
  return []
