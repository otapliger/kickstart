from src.ansi_codes import bold, green, white, blue, reset, yellow

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
{green}Welcome to void.kickstart, a Void Linux installer.{reset}"""

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
{blue}Welcome to arch.kickstart, an Arch Linux installer.{reset}"""

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
{yellow}Welcome to linux.kickstart, a Linux installer.{reset}"""


def print_logo(distro_id: str) -> str:
  logos = {
    "void": void,
    "arch": arch,
    "linux": linux,
  }
  print(logos.get(distro_id))
