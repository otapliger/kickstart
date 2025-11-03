import sys
import shutil
from src.ansi_codes import green, reset

# ANSI escape codes as named constants
SAVE_CURSOR = "\033[s"
RESTORE_CURSOR = "\033[u"
MOVE_TO_BOTTOM = "\033[9999;0H"
CLEAR_LINE = "\033[2K"


def truncate_to_fit(text: str, max_width: int) -> str:
  """Truncate text to fit within max_width, adding ellipsis if needed."""
  if len(text) <= max_width - 1:
    return text
  return text[: max_width - 4] + "..."


def format_status(text: str, width: int) -> str:
  """Format status text with color and truncation."""
  truncated = truncate_to_fit(text, width)
  return f"{green}{truncated}{reset}"


def write_at_bottom(text: str) -> None:
  """Write text at the bottom of the terminal with cursor save/restore."""
  _ = sys.stdout.write(SAVE_CURSOR)
  _ = sys.stdout.write(MOVE_TO_BOTTOM)
  _ = sys.stdout.write(CLEAR_LINE)
  _ = sys.stdout.write(text)
  _ = sys.stdout.write(RESTORE_CURSOR)
  _ = sys.stdout.flush()


class StatusLine:
  """Manages a fixed status line at the bottom of the terminal."""

  def __init__(self):
    self.enabled: bool = sys.stdout.isatty()
    self.current_status: str = ""

  def update(self, message: str) -> None:
    """Update the status line with a new message."""
    if not self.enabled:
      print(f"{green}{message}{reset}")
      return

    self.current_status = message
    self._render()

  def _render(self) -> None:
    """Render the status line at the bottom of the terminal."""
    terminal_width = shutil.get_terminal_size().columns
    status_text = format_status(self.current_status, terminal_width)
    write_at_bottom(status_text)

  def clear(self) -> None:
    """Clear the status line."""
    if not self.enabled:
      return

    write_at_bottom("")
    self.current_status = ""
