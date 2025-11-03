import sys
import shutil
import signal
from types import FrameType
from collections.abc import Callable
from typing import TextIO
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
  return f"\033[{row};{col}H"


def set_scroll_region(top: int, bottom: int) -> str:
  return f"\033[{top};{bottom}r"


def reset_scroll_region() -> str:
  return "\033[r"


def truncate_to_fit(text: str, max_width: int) -> str:
  if len(text) <= max_width - 1:
    return text
  return text[: max_width - 4] + "..."


class OutputInterceptor:
  def __init__(self, header: "FixedHeader", original_stdout: TextIO):
    self.header: FixedHeader = header
    self.original_stdout: TextIO = original_stdout
    self.last_write_ended_newline: bool = True

  def write(self, text: str) -> int:
    result = self.original_stdout.write(text)
    if self.header.enabled and not self.header._is_redrawing and text:
      if text == "\n" and self.last_write_ended_newline:
        self.header.step_output.append("")

      elif text != "\n":
        self.header.step_output.append(text.rstrip("\n"))

      self.last_write_ended_newline = text.endswith("\n")

      if "\n" in text:
        self.header._cursor_line += text.count("\n")
        self.header._cursor_col = 1

      else:
        self.header._cursor_col += len(text)

    return result

  def flush(self) -> None:
    return self.original_stdout.flush()


class FixedHeader:
  def __init__(self):
    self._cursor_col: int = 1
    self._cursor_line: int = 0
    self._interceptor: OutputInterceptor | None = None
    self._is_redrawing: bool = False
    self._original_stdout: TextIO = sys.stdout
    self._sigwinch_handler: Callable[[int, FrameType | None], None] | signal.Handlers | int | None = None
    self.enabled: bool = sys.stdout.isatty()
    self.header_height: int = 0
    self.header_lines: list[str] = []
    self.initialized: bool = False
    self.status_position: int = 0
    self.status_text: str = ""
    self.step_output: list[str] = []
    self.terminal_height: int = 0
    self.terminal_width: int = 0

  def set_header_content(self, lines: list[str], status_position: int) -> None:
    if not self.enabled:
      return

    self.header_lines = lines
    self.status_position = status_position
    self.header_height = len(lines)
    self._update_terminal_size()

  def _update_terminal_size(self) -> None:
    size = shutil.get_terminal_size()
    self.terminal_height = size.lines
    self.terminal_width = size.columns

  def _handle_resize(self, _signum: int, _frame: FrameType | None) -> None:
    if not self.enabled or not self.initialized:
      return

    last_height = self.terminal_height
    last_width = self.terminal_width
    self._update_terminal_size()

    if last_height == self.terminal_height and last_width == self.terminal_width:
      return

    self._redraw_header()

  def _redraw_header(self) -> None:
    if not self.enabled or not self.initialized:
      return

    min_height = self.header_height + 3
    if self.terminal_height < min_height:
      return

    self._is_redrawing = True
    sys.stdout.write(reset_scroll_region())
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.write(MOVE_HOME)

    for line in self.header_lines:
      sys.stdout.write(line + "\n")

    scroll_start = self.header_height + 1
    sys.stdout.write(set_scroll_region(scroll_start, self.terminal_height))
    sys.stdout.write(move_to(scroll_start, 1))
    self._cursor_line = 0
    self._cursor_col = 1

    for i, line in enumerate(self.step_output):
      if i < len(self.step_output) - 1:
        print(line)

      else:
        sys.stdout.write(line)
        sys.stdout.flush()

    if self._cursor_line > 0 or self._cursor_col > 1:
      target_row = scroll_start + self._cursor_line
      sys.stdout.write(move_to(target_row, self._cursor_col))

    if self.status_text:
      sys.stdout.write(SAVE_CURSOR)
      sys.stdout.write(move_to(self.status_position, 1))
      sys.stdout.write(self._format_status_line(self.status_text))
      sys.stdout.write(RESTORE_CURSOR)

    sys.stdout.flush()
    self._is_redrawing = False

  def initialize(self) -> None:
    if not self.enabled or self.initialized:
      return

    self._update_terminal_size()
    min_height = self.header_height + 3

    if self.terminal_height < min_height:
      return

    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.write(MOVE_HOME)

    for line in self.header_lines:
      sys.stdout.write(line + "\n")

    scroll_start = self.header_height + 1
    sys.stdout.write(set_scroll_region(scroll_start, self.terminal_height))
    sys.stdout.write(move_to(scroll_start, 1))
    sys.stdout.write(SHOW_CURSOR)
    sys.stdout.flush()

    self.initialized = True
    self._sigwinch_handler = signal.signal(signal.SIGWINCH, self._handle_resize)
    self._original_stdout = sys.stdout
    self._interceptor = OutputInterceptor(self, self._original_stdout)
    sys.stdout = self._interceptor

  def _format_status_line(self, text: str) -> str:
    truncated = truncate_to_fit(text, self.terminal_width)
    padded = truncated.ljust(self.terminal_width)
    return f"{green}{padded}{reset}"

  def clear_step_output(self) -> None:
    self.step_output = []
    self._cursor_line = 0
    self._cursor_col = 1

  def update_status(self, message: str) -> None:
    if not self.enabled:
      print(f"{green}{message}{reset}")
      return

    if not self.initialized:
      return

    self.status_text = message
    self._is_redrawing = True
    sys.stdout.write(SAVE_CURSOR)
    sys.stdout.write(move_to(self.status_position, 1))
    sys.stdout.write(CLEAR_LINE)
    sys.stdout.write(self._format_status_line(message))
    sys.stdout.write(RESTORE_CURSOR)
    sys.stdout.flush()
    self._is_redrawing = False

  def cleanup(self) -> None:
    if not self.enabled or not self.initialized:
      return

    if self._sigwinch_handler is not None:
      signal.signal(signal.SIGWINCH, self._sigwinch_handler)
      self._sigwinch_handler = None

    if self._interceptor is not None:
      sys.stdout = self._original_stdout
      self._interceptor = None

    sys.stdout.write(reset_scroll_region())
    sys.stdout.write(SAVE_CURSOR)
    sys.stdout.write(move_to(self.status_position, 1))
    sys.stdout.write(CLEAR_LINE)
    sys.stdout.write(RESTORE_CURSOR)
    sys.stdout.flush()

    self.initialized = False
