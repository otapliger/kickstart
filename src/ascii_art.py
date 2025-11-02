from src.ansi_codes import bold, green, white, blue, reset, yellow

linux: str = f"""{white}
     ___
    |.. |
    |{yellow}<> {white}|
   / __  \\
  ( /  \\ /|
 {yellow}_{white}/\\ __{white})/{yellow}_{white})
 {yellow}\\/{white}-____{yellow}\\/{bold}{white}

█▄▀ █ █▀▀ █▄▀ █▀ ▀█▀ ▄▀█ █▀█ ▀█▀
█░█ █ █▄▄ █░█ ▄█  █  █▀█ █▀▄  █
{yellow}Welcome to kickstart, a Linux installer.{reset}"""

arch: str = f"""{bold}{blue}
       /\\
      /  \\
     /\\   \\
    /      \\
   /   ,,   \\
  /   |  |  -\\
 /_-''    ''-_\\{bold}{white}

█▄▀ █ █▀▀ █▄▀ █▀ ▀█▀ ▄▀█ █▀█ ▀█▀
█░█ █ █▄▄ █░█ ▄█  █  █▀█ █▀▄  █
{blue}Welcome to kickstart, an Arch Linux installer.{reset}"""

void: str = f"""{bold}{green}
     _______
  _ \\______ -
 | \\  ___  \\ |
 | | /   \\ | |
 | | \\___/ | |
 | \\______ \\_|
  -_______\\{bold}{white}

█▄▀ █ █▀▀ █▄▀ █▀ ▀█▀ ▄▀█ █▀█ ▀█▀
█░█ █ █▄▄ █░█ ▄█  █  █▀█ █▀▄  █
{green}Welcome to kickstart, a Void Linux installer.{reset}"""


def print_logo(distro_id: str) -> None:
  logos = {
    "linux": linux,
    "arch": arch,
    "void": void,
  }
  print(logos.get(distro_id, linux))
