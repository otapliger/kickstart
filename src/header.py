import sys
import shutil
from src.ansi_codes import green, reset

# ANSI escape codes
SAVE_CURSOR = "\033[s"
RESTORE_CURSOR = "\033[u"
CLEAR_SCREEN = "\033[2J"
MOVE_HOME = "\033[H"
CLEAR_LINE = "\033[2K"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"


def move_to(row: int, col: int = 1) -> str:
  """Generate ANSI code to move cursor to specific position."""
  return f"\033[{row};{col}H"


def set_scroll_region(top: int, bottom: int) -> str:
  """Generate ANSI code to set scrolling region (1-indexed)."""
  return f"\033[{top};{bottom}r"


def reset_scroll_region() -> str:
  """Reset scrolling region to full screen."""
  return "\033[r"


def truncate_to_fit(text: str, max_width: int) -> str:
  """Truncate text to fit within max_width, adding ellipsis if needed."""
  if len(text) <= max_width - 1:
    return text
  return text[: max_width - 4] + "..."


class FixedHeader:
  """Manages a fixed header at the top with scrolling content below."""

  def __init__(self):
    self.enabled: bool = sys.stdout.isatty()
    self.header_lines: list[str] = []
    self.status_text: str = ""
    self.status_position: int = 0
    self.header_height: int = 0
    self.terminal_height: int = 0
    self.terminal_width: int = 0
    self.initialized: bool = False

  def set_header_content(self, lines: list[str], status_position: int) -> None:
    """Set the static header content (logo, config, etc) and status bar position."""
    if not self.enabled:
      return

    self.header_lines = lines
    self.status_position = status_position
    self.header_height = len(lines)
    self._update_terminal_size()

  def _update_terminal_size(self) -> None:
    """Update cached terminal dimensions."""
    size = shutil.get_terminal_size()
    self.terminal_height = size.lines
    self.terminal_width = size.columns

  def initialize(self) -> None:
    """Initialize the fixed header and scrolling region."""
    if not self.enabled or self.initialized:
      return

    self._update_terminal_size()
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.write(MOVE_HOME)

    # Print header content
    for line in self.header_lines:
      sys.stdout.write(line + "\n")

    # Set scrolling region (below header)
    scroll_start = self.header_height + 1
    sys.stdout.write(set_scroll_region(scroll_start, self.terminal_height))

    # Move cursor to start of scrolling region
    sys.stdout.write(move_to(scroll_start, 1))

    # Show cursor again
    sys.stdout.write(SHOW_CURSOR)
    sys.stdout.flush()

    self.initialized = True

  def _format_status_line(self, text: str) -> str:
    """Format status line with color and padding."""
    truncated = truncate_to_fit(text, self.terminal_width)
    padded = truncated.ljust(self.terminal_width)
    return f"{green}{padded}{reset}"

  def update_status(self, message: str) -> None:
    """Update the status bar in the fixed header."""
    if not self.enabled:
      print(f"{green}{message}{reset}")
      return

    if not self.initialized:
      return

    self.status_text = message
    sys.stdout.write(SAVE_CURSOR)
    sys.stdout.write(move_to(self.status_position, 1))
    sys.stdout.write(CLEAR_LINE)
    sys.stdout.write(self._format_status_line(message))
    sys.stdout.write(RESTORE_CURSOR)
    sys.stdout.flush()

  def cleanup(self) -> None:
    """Reset terminal state."""
    if not self.enabled or not self.initialized:
      return

    sys.stdout.write(reset_scroll_region())
    sys.stdout.write(SAVE_CURSOR)
    sys.stdout.write(move_to(self.status_position, 1))
    sys.stdout.write(CLEAR_LINE)
    sys.stdout.write(RESTORE_CURSOR)
    sys.stdout.flush()

    self.initialized = False
