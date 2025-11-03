from src.ansi_codes import bold, green, white, blue, reset, yellow

# ============================================================================
# Distros
# ============================================================================
# ARCH LINUX
_arch_logo: str = f"""{bold}{blue}
       /\\
      /  \\
     /\\   \\
    /      \\
   /   ,,   \\
  /   |  |  -\\
 /_-''    ''-_\\{reset}"""

# ============================================================================
# VOID LINUX
_void_logo: str = f"""{bold}{green}
     _______
  _ \\______ -
 | \\  ___  \\ |
 | | /   \\ | |
 | | \\___/ | |
 | \\______ \\_|
  -_______\\{reset}"""

# ============================================================================
# TUX ASCII art
# ============================================================================
_linux_logo: str = f"""{white}
     ___
    |.. |
    |{yellow}<> {white}|
   / __  \\
  ( /  \\ /|
 {yellow}_{white}/\\ __{white})/{yellow}_{white})
 {yellow}\\/{white}-____{yellow}\\/{reset}"""

# ============================================================================
# KICKSTART ASCII art
# ============================================================================
_kickstart_text: str = f"""{bold}{white}
█▄▀ █ █▀▀ █▄▀ █▀ ▀█▀ ▄▀█ █▀█ ▀█▀
█░█ █ █▄▄ █░█ ▄█  █  █▀█ █▀▄  █{reset}"""


def _buid_kickstart_logo(logo: str, tagline_color: str, tagline_text: str) -> str:
  return f"{logo}\n{_kickstart_text}\n{tagline_color}{tagline_text}{reset}"


def print_logo(distro_id: str) -> None:
  logos = {
    "arch": _buid_kickstart_logo(_arch_logo, blue, "Arch Linux installer, simplified."),
    "void": _buid_kickstart_logo(_void_logo, green, "Void Linux installer, simplified."),
  }
  print(logos.get(distro_id, _buid_kickstart_logo(_linux_logo, yellow, "Linux installer, simplified.")))
