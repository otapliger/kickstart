import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


class TUI:
  def __init__(self):
    self.enabled: bool = sys.stdout.isatty()
    self.status_text: str = ""
    self.initialized: bool = False

  def initialize(self) -> None:
    if not self.enabled or self.initialized:
      return
    self.initialized = True

  def update_status(self, message: str) -> None:
    if not self.enabled:
      console.print(f"[bold green]{message}[/]")
      return

    if not self.initialized:
      return

    self.status_text = message
    status = Text(self.status_text, style="bold green")
    panel = Panel(status, border_style="green", padding=(0, 1))
    console.print(panel)

  def cleanup(self) -> None:
    if not (self.enabled and self.initialized):
      return
    self.initialized = False
