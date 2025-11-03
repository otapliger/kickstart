import sys
import shutil
import signal
from types import FrameType
from collections.abc import Callable
from typing import TextIO
from dataclasses import dataclass
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
  return text if len(text) <= max_width - 1 else text[: max_width - 4] + "..."


def write_sequence(output: TextIO, sequence: str) -> None:
  _ = output.write(sequence)


def write_and_flush(output: TextIO, sequence: str) -> None:
  write_sequence(output, sequence)
  output.flush()


def count_newlines(text: str) -> int:
  return text.count("\n")


def get_terminal_size() -> tuple[int, int]:
  size = shutil.get_terminal_size()
  return size.lines, size.columns


def get_new_cursor_position(text: str, current_line: int, current_col: int) -> tuple[int, int]:
  if "\n" in text:
    return current_line + count_newlines(text), 1
  return current_line, current_col + len(text)


def format_status_line(text: str, terminal_width: int) -> str:
  truncated = truncate_to_fit(text, terminal_width)
  padded = truncated.ljust(terminal_width)
  return f"{green}{padded}{reset}"


@dataclass
class TerminalState:
  cursor_col: int = 1
  cursor_line: int = 0
  terminal_height: int = 0
  terminal_width: int = 0


class OutputInterceptor:
  def __init__(self, header: "FixedHeader", original_stdout: TextIO):
    self.header: FixedHeader = header
    self.original_stdout: TextIO = original_stdout
    self.last_write_ended_newline: bool = True

  def write(self, text: str) -> int:
    result = self.original_stdout.write(text)

    if self.header.enabled and not self.header.is_redrawing and text:
      self._append_to_step_output(text)
      self._update_cursor_tracking(text)

    return result

  def _append_to_step_output(self, text: str) -> None:
    if text == "\n" and self.last_write_ended_newline:
      self.header.step_output.append("")

    elif text != "\n":
      self.header.step_output.append(text.rstrip("\n"))

    self.last_write_ended_newline = text.endswith("\n")

  def _update_cursor_tracking(self, text: str) -> None:
    new_line, new_col = get_new_cursor_position(text, self.header.state.cursor_line, self.header.state.cursor_col)
    self.header.state.cursor_line = new_line
    self.header.state.cursor_col = new_col

  def flush(self) -> None:
    return self.original_stdout.flush()


class FixedHeader:
  def __init__(self):
    self.state: TerminalState = TerminalState()
    self.interceptor: OutputInterceptor | None = None
    self.is_redrawing: bool = False
    self.original_stdout: TextIO = sys.stdout
    self.sigwinch_handler: Callable[[int, FrameType | None], None] | signal.Handlers | int | None = None
    self.enabled: bool = sys.stdout.isatty()
    self.header_height: int = 0
    self.header_lines: list[str] = []
    self.initialized: bool = False
    self.status_position: int = 0
    self.status_text: str = ""
    self.step_output: list[str] = []

  def set_header_content(self, lines: list[str], status_position: int) -> None:
    if not self.enabled:
      return

    self.header_lines = lines
    self.status_position = status_position
    self.header_height = len(lines)
    self._update_terminal_size()

  def _update_terminal_size(self) -> None:
    height, width = get_terminal_size()
    self.state.terminal_height = height
    self.state.terminal_width = width

  def _has_terminal_size_changed(self, last_height: int, last_width: int) -> bool:
    return last_height != self.state.terminal_height or last_width != self.state.terminal_width

  def _handle_resize(self, _signum: int, _frame: FrameType | None) -> None:
    if not self.enabled or not self.initialized:
      return

    last_height = self.state.terminal_height
    last_width = self.state.terminal_width
    self._update_terminal_size()

    if self._has_terminal_size_changed(last_height, last_width):
      self._redraw_header()

  def _is_terminal_too_small(self) -> bool:
    min_height = self.header_height + 3
    return self.state.terminal_height < min_height

  def _write_header_lines(self) -> None:
    for line in self.header_lines:
      write_sequence(sys.stdout, line + "\n")

  def _write_step_output_lines(self) -> None:
    for i, line in enumerate(self.step_output):
      if i < len(self.step_output) - 1:
        _ = print(line)

      else:
        write_and_flush(sys.stdout, line)

  def _should_restore_cursor_position(self) -> bool:
    return self.state.cursor_line > 0 or self.state.cursor_col > 1

  def _restore_cursor_to_position(self, scroll_start: int) -> None:
    if self._should_restore_cursor_position():
      target_row = scroll_start + self.state.cursor_line
      write_sequence(sys.stdout, move_to(target_row, self.state.cursor_col))

  def _write_status_if_present(self) -> None:
    if self.status_text:
      write_sequence(sys.stdout, SAVE_CURSOR)
      write_sequence(sys.stdout, move_to(self.status_position, 1))
      write_sequence(sys.stdout, format_status_line(self.status_text, self.state.terminal_width))
      write_sequence(sys.stdout, RESTORE_CURSOR)

  def _reset_cursor_state(self) -> None:
    self.state.cursor_line = 0
    self.state.cursor_col = 1

  def _redraw_header(self) -> None:
    if not self.enabled or not self.initialized or self._is_terminal_too_small():
      return

    self.is_redrawing = True

    # Clear and reset
    write_sequence(sys.stdout, reset_scroll_region())
    write_sequence(sys.stdout, CLEAR_SCREEN)
    write_sequence(sys.stdout, MOVE_HOME)

    # Write header
    self._write_header_lines()

    # Set scroll region
    scroll_start = self.header_height + 1
    write_sequence(sys.stdout, set_scroll_region(scroll_start, self.state.terminal_height))
    write_sequence(sys.stdout, move_to(scroll_start, 1))
    self._reset_cursor_state()

    # Write step output
    self._write_step_output_lines()

    # Restore cursor
    self._restore_cursor_to_position(scroll_start)

    # Write status
    self._write_status_if_present()

    _ = sys.stdout.flush()
    self.is_redrawing = False

  def _setup_terminal_display(self) -> None:
    write_sequence(sys.stdout, CLEAR_SCREEN)
    write_sequence(sys.stdout, HIDE_CURSOR)
    write_sequence(sys.stdout, MOVE_HOME)
    self._write_header_lines()

  def _setup_scroll_region(self) -> None:
    scroll_start = self.header_height + 1
    write_sequence(sys.stdout, set_scroll_region(scroll_start, self.state.terminal_height))
    write_sequence(sys.stdout, move_to(scroll_start, 1))
    write_sequence(sys.stdout, SHOW_CURSOR)
    _ = sys.stdout.flush()

  def _setup_signal_handler(self) -> None:
    self.sigwinch_handler = signal.signal(signal.SIGWINCH, self._handle_resize)

  def _setup_output_interceptor(self) -> None:
    self.original_stdout = sys.stdout
    self.interceptor = OutputInterceptor(self, self.original_stdout)
    sys.stdout = self.interceptor

  def initialize(self) -> None:
    if not self.enabled or self.initialized:
      return

    self._update_terminal_size()

    if self._is_terminal_too_small():
      return

    self._setup_terminal_display()
    self._setup_scroll_region()
    self.initialized = True
    self._setup_signal_handler()
    self._setup_output_interceptor()

  def clear_step_output(self) -> None:
    self.step_output = []
    self._reset_cursor_state()

  def _write_status_update(self, message: str) -> None:
    write_sequence(sys.stdout, SAVE_CURSOR)
    write_sequence(sys.stdout, move_to(self.status_position, 1))
    write_sequence(sys.stdout, CLEAR_LINE)
    write_sequence(sys.stdout, format_status_line(message, self.state.terminal_width))
    write_sequence(sys.stdout, RESTORE_CURSOR)
    _ = sys.stdout.flush()

  def update_status(self, message: str) -> None:
    if not self.enabled:
      _ = print(f"{green}{message}{reset}")
      return

    if not self.initialized:
      return

    self.status_text = message
    self.is_redrawing = True
    self._write_status_update(message)
    self.is_redrawing = False

  def _cleanup_signal_handler(self) -> None:
    if self.sigwinch_handler is not None:
      _ = signal.signal(signal.SIGWINCH, self.sigwinch_handler)
      self.sigwinch_handler = None

  def _cleanup_output_interceptor(self) -> None:
    if self.interceptor is not None:
      sys.stdout = self.original_stdout
      self.interceptor = None

  def _cleanup_status_line(self) -> None:
    write_sequence(sys.stdout, reset_scroll_region())
    write_sequence(sys.stdout, SAVE_CURSOR)
    write_sequence(sys.stdout, move_to(self.status_position, 1))
    write_sequence(sys.stdout, CLEAR_LINE)
    write_sequence(sys.stdout, RESTORE_CURSOR)
    _ = sys.stdout.flush()

  def cleanup(self) -> None:
    if not self.enabled or not self.initialized:
      return

    self._cleanup_signal_handler()
    self._cleanup_output_interceptor()
    self._cleanup_status_line()
    self.initialized = False
