#!/usr/bin/env python3
"""Record the README GIF from the real, deterministic EnvBisect demo output.

Run from any directory with ``python scripts/record-demo.py``. Requires Pillow.
The renderer changes only presentation and timing; every displayed result line is
copied from a fresh invocation of the CLI.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:
    raise SystemExit("Pillow is required: python -m pip install Pillow") from exc


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "assets" / "envbisect-demo.gif"
COMMAND = [
    "envbisect",
    "diagnose",
    "--pass",
    "examples/demo/pass.env",
    "--fail",
    "examples/demo/fail.env",
    "--",
    "python",
    "examples/demo/app.py",
]

# The single command is wrapped with a shell continuation only for display.
INTRO = "# 46 environment differences -> 2 that matter"
PROMPT = [
    "$ envbisect diagnose --pass examples/demo/pass.env \\",
    "  --fail examples/demo/fail.env -- python examples/demo/app.py",
]

# Reveal actual output through the two verification lines. The final screen
# retains the 46 count, the two variables, their interaction, and verification.
EVENTS = [
    (0.00, None),
    (0.85, "command"),
    (1.75, "EnvBisect"),
    (2.15, "Checking baselines..."),
    (2.65, "  PASS environment -> PASS"),
    (3.10, "  FAIL environment -> FAIL"),
    (3.75, "46 environment differences found."),
    (5.35, "Minimizing failure-inducing changes..."),
    (6.15, "  1 experiments completed; latest:"),
    (7.05, "  10 experiments completed; latest:"),
    (8.05, "Minimal failure-inducing set (1-minimal under the tested conditions):"),
    (9.15, "  FEATURE_CACHE"),
    (10.00, "    0 -> 1"),
    (10.80, "  TZ"),
    (11.65, "    Asia/Kolkata -> UTC"),
    (12.45, "These changes act together in the observed failure."),
    (13.70, "Verification"),
    (14.55, "  PASS + changes -> FAIL 5/5"),
    (15.35, "  FAIL - changes -> PASS 5/5"),
]
DURATION_SECONDS = 19.8

WIDTH, HEIGHT = 1000, 620
TEXT_X, TEXT_Y = 38, 79
LINE_HEIGHT, VISIBLE_ROWS = 27, 19
FONT_SIZE = 21
BG = "#0b1120"
TERMINAL = "#111a2b"
BAR = "#1a2539"
BORDER = "#35425a"
TEXT = "#d7e0ed"
MUTED = "#91a1b8"
ACCENT = "#7fd8f5"
WARM = "#ffd887"
GOOD = "#91e6bd"


def capture_output() -> list[str]:
    if not shutil.which("envbisect") or not shutil.which("python"):
        raise SystemExit("Install the checkout first: python -m pip install -e .")
    result = subprocess.run(
        COMMAND,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode:
        details = result.stderr or result.stdout
        raise SystemExit(
            f"Demo command failed with exit code {result.returncode}:\n{details}"
        )
    lines = result.stdout.splitlines()
    normalized = [line.replace("→", "->") for line in lines]
    required = [marker for _, marker in EVENTS if marker and marker != "command"]
    missing = [
        marker for marker in required if not any(line.startswith(marker) for line in normalized)
    ]
    if missing:
        raise SystemExit(f"Demo output changed; missing expected lines: {missing}")

    final_index = next(
        i for i, line in enumerate(normalized) if line.startswith("  FAIL - changes -> PASS 5/5")
    )
    shown = lines[: final_index + 1]
    # This is a public synthetic fixture. Refuse unexpected report lines so a
    # future CLI change cannot accidentally place host details in the GIF.
    allowed = [
        r"",
        r"EnvBisect",
        r"Checking baselines\.\.\.",
        r"  PASS environment -> PASS \(PASS 3/3\)",
        r"  FAIL environment -> FAIL \(FAIL 3/3\)",
        r"46 environment differences found\.",
        r"Minimizing failure-inducing changes\.\.\.",
        r"  \d+ experiments completed; latest: (PASS|FAIL)",
        r"Minimal failure-inducing set \(1-minimal under the tested conditions\):",
        r"  FEATURE_CACHE",
        r"    0 -> 1",
        r"  TZ",
        r"    Asia/Kolkata -> UTC",
        r"These changes act together in the observed failure\.",
        r"Verification",
        r"  PASS \+ changes -> FAIL 5/5",
        r"  FAIL - changes -> PASS 5/5",
    ]
    for line in shown:
        if not any(re.fullmatch(pattern, line.replace("→", "->")) for pattern in allowed):
            raise SystemExit(f"Unexpected report line; review before publishing: {line!r}")
    return shown


def load_font() -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/CascadiaMono.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "DejaVuSansMono.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, FONT_SIZE)
        except OSError:
            continue
    raise SystemExit(
        "A monospace font is required (Cascadia Mono, Consolas, Menlo, or DejaVu Sans Mono)."
    )


def color_for(line: str) -> str:
    normalized = line.replace("→", "->")
    if line.startswith("#") or (line.startswith("  ") and "experiments completed" in line):
        return MUTED
    if line.startswith("$") or line.startswith("  --fail"):
        return TEXT
    if normalized.startswith("46 environment"):
        return ACCENT
    if normalized.startswith("  FEATURE_CACHE") or normalized.startswith("  TZ"):
        return WARM
    if normalized.startswith("These changes act together"):
        return WARM
    if normalized.startswith("  PASS + changes") or normalized.startswith("  FAIL - changes"):
        return GOOD
    return TEXT


def frame(font: ImageFont.FreeTypeFont, lines: list[str]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (12, 12, WIDTH - 12, HEIGHT - 12),
        radius=14,
        fill=TERMINAL,
        outline=BORDER,
        width=2,
    )
    draw.rounded_rectangle((13, 13, WIDTH - 13, 63), radius=13, fill=BAR)
    draw.rectangle((13, 49, WIDTH - 13, 63), fill=BAR)
    for x, fill in ((34, "#ff7b72"), (55, "#e3c36a"), (76, "#7bd7a8")):
        draw.ellipse((x - 6, 31, x + 6, 43), fill=fill)
    draw.text((WIDTH // 2, 36), "envbisect / demo", anchor="mm", font=font, fill=MUTED)

    visible = lines[-VISIBLE_ROWS:]
    for row, line in enumerate(visible):
        draw.text((TEXT_X, TEXT_Y + row * LINE_HEIGHT), line, font=font, fill=color_for(line))
    return image


def main() -> None:
    output = capture_output()
    normalized = [line.replace("→", "->") for line in output]
    font = load_font()
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    longest = max([INTRO, *PROMPT, *output], key=lambda line: measure.textlength(line, font=font))
    if measure.textlength(longest, font=font) > WIDTH - 2 * TEXT_X:
        raise SystemExit(f"Terminal line is too wide at {FONT_SIZE}px: {longest!r}")
    final_visible = normalized[-VISIBLE_ROWS:]
    for marker in (
        "46 environment differences found.",
        "  FEATURE_CACHE",
        "  TZ",
        "These changes act together in the observed failure.",
        "  PASS + changes -> FAIL 5/5",
        "  FAIL - changes -> PASS 5/5",
    ):
        if not any(line.startswith(marker) for line in final_visible):
            raise SystemExit(f"Final GIF frame would hide a key result: {marker}")

    images: list[Image.Image] = []
    durations: list[int] = []
    for index, (at, marker) in enumerate(EVENTS):
        displayed = [INTRO]
        if index >= 1:
            displayed += ["", *PROMPT, ""]
        if marker not in (None, "command"):
            until = next(i for i, line in enumerate(normalized) if line.startswith(marker))
            displayed += output[: until + 1]
        images.append(frame(font, displayed))
        next_at = EVENTS[index + 1][0] if index + 1 < len(EVENTS) else DURATION_SECONDS
        durations.append(round((next_at - at) * 1000))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        OUTPUT,
        save_all=True,
        append_images=images[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({DURATION_SECONDS:.1f}s, {len(images)} frames)")


if __name__ == "__main__":
    main()
