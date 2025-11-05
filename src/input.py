from rich.console import Console
from rich.prompt import Prompt, PromptBase
from src.validations import (
  validate_hostname,
  validate_username,
  validate_password,
)

console = Console()


class HostnamePrompt:
  @classmethod
  def ask(cls, message: str, default: str | None) -> str:
    while True:
      host = Prompt.ask(message, default=default, show_default=bool(default))
      if not validate_hostname(host):
        console.print("\n[prompt.invalid]Invalid hostname - must follow RFC 1123 (letters, digits, hyphens).[/]")
        continue
      return host


class IntegerPrompt(PromptBase[int]):
  response_type = int
  validate_error_message = "\n[prompt.invalid]Please enter a valid integer number"
  illegal_choice_message = "\n[prompt.invalid.choice]Please select one of the available options"


class UsernamePrompt:
  @classmethod
  def ask(cls, message: str) -> str:
    while True:
      user_name = Prompt.ask(message)
      if not validate_username(user_name):
        console.print("\n[prompt.invalid]Invalid username - use letters, digits, hyphen or underscore.[/]")
        continue
      return user_name


class PasswordPrompt:
  @classmethod
  def ask(cls, message: str) -> str:
    while True:
      user_pass = Prompt.ask(message, password=True)
      if not validate_password(user_pass):
        console.print("\n[prompt.invalid]Invalid password - try again.[/]")
        continue

      user_pass_check = Prompt.ask("Verify the password", password=True)
      if user_pass != user_pass_check:
        console.print("\n[prompt.invalid]Passwords don't match, please try again.[/]")
        continue

      return user_pass
