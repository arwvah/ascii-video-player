"""POSIX-only integration checks using a real pseudo-terminal."""
import errno
import os
import pty
import select
import signal
import subprocess
import sys
import time


def run(arguments: list[str], interrupt: bool = False) -> None:
    master, slave = pty.openpty()
    process = subprocess.Popen([sys.executable, "ascii_video.py", *arguments],
                               stdin=slave, stdout=slave, stderr=slave)
    os.close(slave)
    data = bytearray()
    started = time.monotonic()
    signaled = False
    try:
        while True:
            elapsed = time.monotonic()-started
            if elapsed > 10:
                raise RuntimeError("Playback timed out")
            if interrupt and elapsed > 1 and not signaled:
                process.send_signal(signal.SIGINT)
                signaled = True
            if select.select([master], [], [], .05)[0]:
                try:
                    block = os.read(master, 65536)
                except OSError as error:
                    if error.errno == errno.EIO:
                        break
                    raise
                if not block:
                    break
                data.extend(block)
        status = process.wait(timeout=2)
        assert status == (130 if interrupt else 0), (status, data[-1000:])
        assert b"\x1b[?25l" in data
        assert b"\x1b[?25h\x1b[?1049l" in data
        assert data.count(b"\x1b[H") > 2
        print(f"PASS {arguments or ['default candle']} ({len(data)} bytes; restored cursor; exit {status})")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        os.close(master)


if __name__ == "__main__":
    run([], interrupt=True)
    run(["--candle", "--end", "0.5", "--color", "ansi"])
    run(["sample.mp4", "--width", "60"])
    run(["sample.mp4", "--width", "30", "--color", "none", "--end", "0.2", "--loop"], interrupt=True)
