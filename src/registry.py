"""
Embedded profile registry for distribution as a single binary.

This module stores profile data as Python constants, allowing profiles
to be compiled into the Nuitka binary without needing external files.
Profiles are keyed by (distro_id, profile_name) for easy lookup.
"""

from typing import Final

PROFILES: Final[dict[tuple[str, str], dict[str, object]]] = {
  ("linux", "test"): {
    "name": "Minimal System for testing",
    "description": "Linux installation for testing",
    "distro": "linux",
    "config": {
      "libc": "glibc",
      "timezone": "Europe/London",
      "keymap": "uk",
      "locale": "en_GB.UTF-8",
    },
    "packages": {"additional": [], "exclude": []},
    "post_install_commands": [],
  },
  ("void", "niri"): {
    "name": "Niri Wayland",
    "description": "Niri compositor with multimedia support",
    "distro": "void",
    "config": {
      "libc": "glibc",
      "timezone": "Europe/London",
      "keymap": "uk",
      "locale": "en_GB.UTF-8",
    },
    "packages": {
      "additional": [
        "Thunar",
        "alacritty",
        "dunst",
        "elogind",
        "firefox",
        "fuzzel",
        "keepassxc",
        "libnotify",
        "mesa",
        "mpv",
        "nerd-fonts",
        "niri",
        "noto-fonts-cjk",
        "noto-fonts-emoji",
        "noto-fonts-ttf",
        "optipng",
        "pipewire",
        "polkit",
        "sassc",
        "starship",
        "tumbler",
        "vulkan-loader",
        "wireplumber",
        "xdg-desktop-portal-gtk",
        "xdg-user-dirs",
        "xdg-utils",
        "xfce4-settings",
        "xfconf",
        "zoxide",
      ],
      "exclude": [],
    },
    "post_install_commands": [
      "ln -sf /etc/sv/dbus /var/service/",
      "ln -sf /etc/sv/elogind /var/service/",
      "ln -sf /etc/sv/pipewire /var/service/",
      "ln -sf /etc/sv/wireplumber /var/service/",
    ],
  },
}


def get_embedded_profile(distro_id: str, profile_name: str) -> dict[str, object] | None:
  """
  Get an embedded profile by distro_id and profile name.

  Args:
      distro_id: Distribution identifier (e.g., 'void', 'arch')
      profile_name: Profile name without extension (e.g., 'niri')

  Returns:
      Profile data as a dictionary, or None if not found
  """
  return PROFILES.get((distro_id, profile_name))


def list_profiles_for_distro(distro_id: str) -> list[str]:
  """
  List all available profile names for a given distro.

  Args:
      distro_id: Distribution identifier

  Returns:
      List of available profile names
  """
  return sorted([name for distro, name in PROFILES.keys() if distro == distro_id])
