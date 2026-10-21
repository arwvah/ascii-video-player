"""ANSI terminal lifecycle, including Windows virtual terminal support."""
import os
import shutil
import sys


def terminal_size() -> tuple[int, int]:
    """Reserve the last column/row to avoid wrapping and scrolling."""
    size = shutil.get_terminal_size((100, 32))
    return max(1, min(size.columns - 1, 300)), max(1, min(size.lines - 1, 150))


class Terminal:
    """Restore the cursor, colors, alternate screen and Windows mode on exit."""
    def __init__(self) -> None:
        self.windows_state = None

    def __enter__(self) -> "Terminal":
        if not sys.stdout.isatty():
            raise ValueError("Playback needs an interactive terminal; use --export for a file")
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.windll.kernel32
            kernel.GetStdHandle.restype = wintypes.HANDLE
            handle = kernel.GetStdHandle(-11)
            mode = wintypes.DWORD()
            if not kernel.GetConsoleMode(handle, ctypes.byref(mode)) or not kernel.SetConsoleMode(handle, mode.value | 4):
                raise ValueError("Enable a modern ANSI terminal, such as Windows Terminal")
            self.windows_state = kernel, handle, mode.value
        sys.stdout.write("\x1b[?1049h\x1b[?25l\x1b[2J\x1b[H")
        sys.stdout.flush()
        return self

    def draw(self, text: str) -> None:
        sys.stdout.write("\x1b[H" + text + "\x1b[0m\x1b[J")
        sys.stdout.flush()

    def __exit__(self, *exc: object) -> None:
        try:
            sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
            sys.stdout.flush()
        finally:
            if self.windows_state:
                kernel, handle, mode = self.windows_state
                kernel.SetConsoleMode(handle, mode)
