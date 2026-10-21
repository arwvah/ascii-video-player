# Verification

Verified on Linux with Python 3.13.15 in the project `.venv`.
Dependencies installed: NumPy 2.5.4, OpenCV headless 4.14.0.94,
Pillow 12.3.0, pytest 9.1.1. FFmpeg was available on PATH.

- Dependency installation and editable console entry point: passed.
- Automated tests: 28 passed. Covers brightness/inversion, landscape and portrait
  sizing, tiny and huge terminals, color encoding, absolute timing/skip calculation,
  CLI validation, corrupted/missing input, seeded candle movement, restoration on
  interruption, export resampling/trimming, missing-FFmpeg warning, overwrite
  protection, forced replacement, source protection and backward seeking.
- CLI `--help` and Python compilation: passed.
- Real POSIX pseudo-terminal checks: default candle interrupted with SIGINT,
  finite ANSI candle, truecolor video playback, and looping monochrome playback
  interrupted with SIGINT. All emitted cursor hide/restore and alternate-screen
  exit sequences, with expected exit statuses (0 or 130).
- Synthetic landscape video: 48 frames at 24 FPS, two seconds; terminal playback
  and MP4 export passed.
- Candle export: 30 frames at 30 FPS, one second; decoded preview inspected.
- Synthetic portrait MP4 export: passed using the installed `ascii-video` command.
- Audio trim/resample: a generated 440 Hz AAC source was exported from 0.25 to
  1.5 seconds at 20 FPS. ffprobe confirmed 25 video frames, 1.250000 seconds of
  video, and 1.250000 seconds of AAC audio.

Generated samples were used for these checks and removed during publication cleanup:
`sample.mp4`, `sample-ascii.mp4`, `sample-audio.mp4`,
`sample-audio-ascii.mp4`, `candle-ascii.mp4`, `portrait.mp4`,
and `portrait-ascii.mp4`. Recreate samples with `scripts/make_sample.py` and the
export commands in the README.

Limitations: Windows/macOS were not executed here. Variable-frame-rate sources
use nominal FPS. Terminal playback has no audio. Exports use MPEG-4 Part 2 video,
which is suitable for desktop players but not supported by every web browser.
Visual inspection covered an exported candle frame; terminal smoke checks verified
output and lifecycle through a pseudo-terminal, not a graphical terminal screenshot.
