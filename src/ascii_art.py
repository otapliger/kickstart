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
{yellow}Linux installer, simplified.{reset}"""

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
{blue}Arch Linux installer, simplified.{reset}"""

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
{green}Void Linux installer, simplified.{reset}"""


def print_logo(distro_id: str) -> None:
  logos = {
    "linux": linux,
    "arch": arch,
    "void": void,
  }
  print(logos.get(distro_id, linux))
