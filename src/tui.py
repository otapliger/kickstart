import shutil
import sys
import time

from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

console = Console()

STEP_PREFIXES = {
  "Settings": "* ",
  "Disk Setup": "# ",
  "System Bootstrap": "^ ",
  "System Installation And Configuration": "@ ",
  "Cleanup": "~ ",
}

DISTRO_COLORS = {
  "arch": {"text": "bold blue", "border": "blue"},
  "void": {"text": "bold green", "border": "green"},
}


class TUI:
  def __init__(self, dry_mode: bool = False, distro_id: str = "arch"):
    self.enabled: bool = sys.stdout.isatty()
    self.status_text: str = ""
    self.initialized: bool = False
    self.live: Live | None = None
    self.layout: Layout | None = None
    self.output_lines: list[str] = []
    self.dry_mode: bool = dry_mode
    self.distro_id: str = distro_id
    self.colors = DISTRO_COLORS.get(distro_id, {"text": "bold yellow", "border": "yellow"})

  def initialize(self) -> None:
    if not self.enabled or self.initialized:
      return
    self.initialized = True

  def _create_status_panel(self, text: str) -> Panel:
    status = Text(text, style=self.colors["text"])
    return Panel(
      status,
      border_style=self.colors["border"],
      padding=(0, 1),
      expand=False,
      box=box.SQUARE,
      title="kickstart",
      title_align="left",
    )

  def update_status(self, message: str, step_name: str = "") -> None:
    if not self.enabled:
      console.print(f"[{self.colors['text']}]{message}[/]")
      return

    if not self.initialized:
      return

    prefix = STEP_PREFIXES.get(step_name)
    self.status_text = f"{prefix}{message}"

    if self.live is None:
      # Initialize Live display on first call (step 1)
      layout = Layout()
      layout.split_column(
        Layout(name="status", size=3),
        Layout(name="output", ratio=1),
      )

      panel = self._create_status_panel(self.status_text)
      layout["status"].update(panel)
      layout["output"].update("")

      self.layout = layout
      self.live = Live(self.layout, console=console, refresh_per_second=10, screen=False)
      self.live.start()

    else:
      if self.layout:
        panel = self._create_status_panel(self.status_text)
        self.layout["status"].update(panel)

  def print(self, message: str) -> None:
    """Print message to output area when Live is active, or console when not."""
    if self.dry_mode:
      time.sleep(0.1)  # Delay in dry mode for testing purposes

    if self.live and self.layout:
      # Add to output buffer and update layout
      self.output_lines.append(message)

      # Calculate visible lines based on terminal height minus status panel
      terminal_height = shutil.get_terminal_size().lines
      # Status panel takes 3 lines, leave some buffer
      visible_lines = max(1, terminal_height - 4)

      # Show only the last N lines that fit on screen
      display_lines = self.output_lines[-visible_lines:]
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
