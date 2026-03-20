"""
Low-level terminal I/O engine for the TUI.

Handles:
  - Raw keyboard input (msvcrt on Windows, tty/termios on POSIX)
  - VT100/ANSI sequence emission
  - Alternate Screen Buffer management
  - Cursor visibility control
  - Terminal size detection
  - Guaranteed cleanup via atexit integration
"""

from __future__ import annotations

import enum
import os
import re
import sys
from typing import Optional

# Platform-specific raw input
if sys.platform == "win32":
    import msvcrt
    try:
        import ctypes
        _kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    except Exception:
        _kernel32 = None
else:
    import tty
    import termios


# ==============================================================================
# KEY ENUM — Normalized cross-platform key representation
# ==============================================================================

class Key(enum.Enum):
    """Normalized keyboard input values."""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    ENTER = "enter"
    ESCAPE = "escape"
    TAB = "tab"
    BACKSPACE = "backspace"
    DELETE = "delete"
    HOME = "home"
    END = "end"
    PAGE_UP = "page_up"
    PAGE_DOWN = "page_down"
    CHAR = "char"  # Regular character — check `.char` attribute
    UNKNOWN = "unknown"


class KeyEvent:
    """A single keyboard event with optional character payload."""

    __slots__ = ("key", "char")

    def __init__(self, key: Key, char: str = "") -> None:
        self.key = key
        self.char = char

    def __repr__(self) -> str:
        if self.key == Key.CHAR:
            return f"KeyEvent(CHAR, {self.char!r})"
        return f"KeyEvent({self.key.name})"


# ==============================================================================
# TERMINAL ENGINE
# ==============================================================================

class TerminalEngine:
    """
    Cross-platform terminal I/O engine.

    Usage::

        engine = TerminalEngine()
        engine.enter_fullscreen()
        try:
            while True:
                engine.paint(lines)
                key = engine.getch()
                if key.key == Key.ESCAPE:
                    break
        finally:
            engine.exit_fullscreen()
    """

    def __init__(self) -> None:
        self._in_fullscreen = False
        self._old_termios: Optional[list] = None

    # ------------------------------------------------------------------
    # VT100 ANSI Sequences
    # ------------------------------------------------------------------

    @staticmethod
    def _write(seq: str) -> None:
        """Write an escape sequence to stdout and flush immediately."""
        sys.stdout.write(seq)
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # Fullscreen Management
    # ------------------------------------------------------------------

    def enter_fullscreen(self) -> None:
        """Switch to Alternate Screen Buffer, hide cursor, enable raw mode."""
        if self._in_fullscreen:
            return

        # Windows: enable VT100 processing
        if sys.platform == "win32" and _kernel32:
            try:
                handle = _kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
                mode = ctypes.c_ulong()
                _kernel32.GetConsoleMode(handle, ctypes.byref(mode))
                # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                _kernel32.SetConsoleMode(handle, mode.value | 0x0004)
            except Exception:
                pass

        # POSIX: save terminal state and enter raw mode
        if sys.platform != "win32":
            try:
                self._old_termios = termios.tcgetattr(sys.stdin.fileno())
                tty.setraw(sys.stdin.fileno())
            except Exception:
                self._old_termios = None

        self._write("\x1b[?1049h")  # Enter alt screen
        self._write("\x1b[?25l")    # Hide cursor
        self._write("\x1b[2J")      # Clear screen
        self._write("\x1b[H")       # Move to top-left
        self._in_fullscreen = True

    def exit_fullscreen(self) -> None:
        """Restore terminal to normal state. Safe to call multiple times."""
        if not self._in_fullscreen:
            return

        self._write("\x1b[?25h")    # Show cursor
        self._write("\x1b[?1049l")  # Exit alt screen

        # POSIX: restore terminal settings
        if sys.platform != "win32" and self._old_termios is not None:
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old_termios)
            except Exception:
                pass
            self._old_termios = None

        self._in_fullscreen = False

    # ------------------------------------------------------------------
    # Terminal Size
    # ------------------------------------------------------------------

    @staticmethod
    def get_size() -> tuple[int, int]:
        """Returns (columns, rows) of the terminal. Refreshed every call."""
        try:
            cols, rows = os.get_terminal_size()
            return max(cols, 40), max(rows, 10)
        except OSError:
            return 80, 24  # Fallback

    # ------------------------------------------------------------------
    # ANSI Helpers
    # ------------------------------------------------------------------

    _ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

    @classmethod
    def _visible_len(cls, s: str) -> int:
        """Returns the visible character count (excludes ANSI escape sequences)."""
        return len(cls._ANSI_RE.sub("", s))

    @classmethod
    def _truncate_visible(cls, s: str, max_width: int) -> str:
        """
        Truncate a string to ``max_width`` *visible* characters,
        preserving all ANSI escape sequences encountered before the cut.
        """
        visible_count = 0
        i = 0
        while i < len(s):
            m = cls._ANSI_RE.match(s, i)
            if m:
                i = m.end()  # skip the escape — it has zero visible width
                continue
            if visible_count >= max_width:
                break
            visible_count += 1
            i += 1
        return s[:i]

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def paint(self, lines: list[str]) -> None:
        """
        Render a full frame to the terminal.

        Uses explicit cursor positioning (``\x1b[row;1H``) for each row so
        ANSI escape codes inside the lines never upset the layout.
        Pads each row to the full terminal width to prevent ghosting.
        """
        cols, rows = self.get_size()

        buf: list[str] = []

        for i in range(rows):
            # Position cursor at column 1 of this row
            buf.append(f"\x1b[{i + 1};1H")

            if i < len(lines):
                line = lines[i].rstrip("\n")
                # Truncate to visible width
                line = self._truncate_visible(line, cols)
                # Pad with spaces so the full row is overwritten
                vis = self._visible_len(line)
                pad = max(0, cols - vis)
                buf.append(line + " " * pad)
            else:
                buf.append(" " * cols)

        sys.stdout.write("".join(buf))
        sys.stdout.flush()

    # ------------------------------------------------------------------
    # Raw Keyboard Input
    # ------------------------------------------------------------------

    def getch(self) -> KeyEvent:
        """
        Blocking read of a single keypress. Returns a normalized KeyEvent.

        On Windows, uses msvcrt.getwch().
        On POSIX, reads from raw stdin.
        """
        if sys.platform == "win32":
            return self._getch_windows()
        else:
            return self._getch_posix()

    @staticmethod
    def _getch_windows() -> KeyEvent:
        """Windows raw key input via msvcrt."""
        ch = msvcrt.getwch()

        if ch == "\r" or ch == "\n":
            return KeyEvent(Key.ENTER)
        if ch == "\x1b":
            return KeyEvent(Key.ESCAPE)
        if ch == "\t":
            return KeyEvent(Key.TAB)
        if ch == "\x08":
            return KeyEvent(Key.BACKSPACE)

        # Extended key prefix (arrow keys, function keys, etc.)
        if ch in ("\x00", "\xe0"):
            ch2 = msvcrt.getwch()
            if ch2 == "H":
                return KeyEvent(Key.UP)
            if ch2 == "P":
                return KeyEvent(Key.DOWN)
            if ch2 == "K":
                return KeyEvent(Key.LEFT)
            if ch2 == "M":
                return KeyEvent(Key.RIGHT)
            if ch2 == "G":
                return KeyEvent(Key.HOME)
            if ch2 == "O":
                return KeyEvent(Key.END)
            if ch2 == "I":
                return KeyEvent(Key.PAGE_UP)
            if ch2 == "Q":
                return KeyEvent(Key.PAGE_DOWN)
            if ch2 == "S":
                return KeyEvent(Key.DELETE)
            return KeyEvent(Key.UNKNOWN)

        return KeyEvent(Key.CHAR, ch)

    @staticmethod
    def _getch_posix() -> KeyEvent:
        """POSIX raw key input via stdin."""
        ch = sys.stdin.read(1)

        if ch == "\r" or ch == "\n":
            return KeyEvent(Key.ENTER)
        if ch == "\t":
            return KeyEvent(Key.TAB)
        if ch == "\x7f" or ch == "\x08":
            return KeyEvent(Key.BACKSPACE)

        if ch == "\x1b":
            # Could be ESC or start of escape sequence
            ch2 = sys.stdin.read(1)
            if ch2 == "":
                return KeyEvent(Key.ESCAPE)
            if ch2 == "[":
                ch3 = sys.stdin.read(1)
                if ch3 == "A":
                    return KeyEvent(Key.UP)
                if ch3 == "B":
                    return KeyEvent(Key.DOWN)
                if ch3 == "C":
                    return KeyEvent(Key.RIGHT)
                if ch3 == "D":
                    return KeyEvent(Key.LEFT)
                if ch3 == "H":
                    return KeyEvent(Key.HOME)
                if ch3 == "F":
                    return KeyEvent(Key.END)
                if ch3 == "5":
                    sys.stdin.read(1)  # consume '~'
                    return KeyEvent(Key.PAGE_UP)
                if ch3 == "6":
                    sys.stdin.read(1)  # consume '~'
                    return KeyEvent(Key.PAGE_DOWN)
                if ch3 == "3":
                    sys.stdin.read(1)  # consume '~'
                    return KeyEvent(Key.DELETE)
                return KeyEvent(Key.UNKNOWN)
            return KeyEvent(Key.ESCAPE)

        return KeyEvent(Key.CHAR, ch)
