from rich.console import Console

console = Console()

# ============================================================================
# Distros
# ============================================================================
# ARCH LINUX
_arch_logo: str = """[bold blue]
       /\\
      /  \\
     /\\   \\
    /      \\
   /   ,,   \\
  /   |  |  -\\
 /_-''    ''-_\\"""

# ============================================================================
# VOID LINUX
_void_logo: str = """[bold green]
     _______
  _ \\______ -
 | \\  ___  \\ |
 | | /   \\ | |
 | | \\___/ | |
 | \\______ \\_|
  -_______\\"""

# ============================================================================
# TUX ASCII art
# ============================================================================
_linux_logo: str = """[white]
     ___
    |.. |
    |[yellow]<> [white]|
   / __  \\
  ( /  \\ /|
 [yellow]_[white]/\\ __[white])/[yellow]_[white])
 [yellow]\\/[white]-____[yellow]\\/"""

# ============================================================================
# KICKSTART ASCII art
# ============================================================================
_kickstart_text: str = """[bold white]
█▄▀ █ █▀▀ █▄▀ █▀ ▀█▀ ▄▀█ █▀█ ▀█▀
█░█ █ █▄▄ █░█ ▄█  █  █▀█ █▀▄  █[/]"""


def _build_kickstart_logo(logo: str, tagline_style: str, tagline_text: str) -> str:
  return f"{logo}\n{_kickstart_text}\n[{tagline_style}]{tagline_text}[/]"


def print_logo(distro_id: str) -> None:
  console.clear()
  logos = {
    "arch": _build_kickstart_logo(_arch_logo, "blue", "Arch Linux installer, simplified."),
    "void": _build_kickstart_logo(_void_logo, "green", "Void Linux installer, simplified."),
  }
  console.print(logos.get(distro_id, _build_kickstart_logo(_linux_logo, "yellow", "Linux installer, simplified.")))
