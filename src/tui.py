import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.layout import Layout

console = Console()


class TUI:
  def __init__(self, dry_mode: bool = False):
    self.enabled: bool = sys.stdout.isatty()
    self.status_text: str = ""
    self.initialized: bool = False
    self.live: Live | None = None
    self.layout: Layout | None = None
    self.output_lines: list[str] = []
    self.dry_mode: bool = dry_mode

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

    if self.live is None:
      # Initialize Live display on first call (step 1)
      layout = Layout()
      layout.split_column(
        Layout(name="status", size=3),
        Layout(name="output", ratio=1),
      )

      status = Text(self.status_text, style="bold green")
      panel = Panel(status, border_style="green", padding=(0, 1))
      layout["status"].update(panel)
      layout["output"].update("")

      self.layout = layout
      self.live = Live(self.layout, console=console, refresh_per_second=10, screen=False)
      self.live.start()

    else:
      if self.layout:
        status = Text(self.status_text, style="bold green")
        panel = Panel(status, border_style="green", padding=(0, 1))
        self.layout["status"].update(panel)

  def print(self, message: str) -> None:
    """Print message to output area when Live is active, or console when not."""
    if self.dry_mode:
      time.sleep(0.1)  # Delay in dry mode for testing purposes

    if self.live and self.layout:
      # Add to output buffer and update layout
      self.output_lines.append(message)

      # Keep last N lines to prevent memory issues
      display_lines = self.output_lines[-100:]
      output_text = "\n".join(display_lines)
      self.layout["output"].update(Text.from_markup(output_text))

    else:
      # Before Live starts, use regular console
      console.print(message)

  def cleanup(self) -> None:
    if not (self.enabled and self.initialized):
      return

    if self.live:
      self.live.stop()
      self.live = None

    self.initialized = False
