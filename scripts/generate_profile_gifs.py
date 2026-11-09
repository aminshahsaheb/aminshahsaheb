from pathlib import Path
from io import BytesIO
import math

import cairosvg
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

# 40 frames at 90 ms gives a calm 3.6-second loop.
# All motion curves return to their starting state without a visible jump.
FRAMES = 40
DURATION_MS = 90
RENDER_SCALE = 2
GIF_COLORS = 128

SOURCES = {
    "profile-hero.svg": ("profile-hero.gif", "hero"),
    "profile-system-map.svg": ("profile-system-map.gif", "map"),
    "profile-operating-system.svg": ("profile-operating-system.gif", "process"),
    "profile-work-grid.svg": ("profile-work-grid.gif", "work"),
    "profile-signal.svg": ("profile-signal.gif", "signal"),
    "profile-connect.svg": ("profile-connect.gif", "connect"),
}

JADE = (151, 211, 176)
BRASS = (215, 189, 135)
BLUE = (151, 184, 211)
COPPER = (190, 132, 111)
PROJECT_ACCENTS = (JADE, BRASS, BLUE)
CONTACT_ACCENTS = ((225, 123, 176), (91, 190, 133), (104, 174, 225), BRASS)
PROCESS_ACCENTS = (JADE, BRASS, BLUE, JADE, COPPER)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def smootherstep(value: float) -> float:
    value = clamp(value)
    return value * value * value * (value * (value * 6 - 15) + 10)


def ping_pong(phase: float) -> float:
    """Smooth travel from 0 to 1 and back to 0, with no endpoint jump."""
    cycle = phase * 2
    raw = cycle if cycle <= 1 else 2 - cycle
    return smootherstep(raw)


def cyclic_focus(phase: float, count: int, index: int) -> float:
    """Soft focus that blends between neighbours instead of switching abruptly."""
    position = (phase % 1.0) * count
    distance = abs(((position - index + count / 2) % count) - count / 2)
    return 1.0 - smootherstep(distance / 1.05)


def render_source(svg_path: Path) -> Image.Image:
    png = cairosvg.svg2png(url=str(svg_path), output_width=800)
    return Image.open(BytesIO(png)).convert("RGB")


def pulse_ring(draw, x, y, radius, alpha, color=JADE, width=2):
    alpha = int(clamp(alpha, 0, 255))
    if alpha <= 0:
        return
    draw.ellipse(
        (x - radius, y - radius, x + radius, y + radius),
        outline=(*color, alpha),
        width=max(1, width),
    )


def add_sweep(layer: Image.Image, x: float, y0: int, y1: int,
              strength: int = 30, color=JADE, half_width: int | None = None):
    width, _ = layer.size
    band = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(band)
    half = half_width or max(14, width // 55)
    draw.rectangle(
        (int(x - half), y0, int(x + half), y1),
        fill=(*color, max(0, min(255, int(strength)))),
    )
    band = band.filter(ImageFilter.GaussianBlur(radius=max(8, width // 90)))
    layer.alpha_composite(band)


def overlay_for(kind: str, size, frame: int) -> Image.Image:
    width, height = size
    phase = frame / FRAMES
    scale = RENDER_SCALE
    sw, sh = width * scale, height * scale
    overlay = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    def point(nx: float, ny: float) -> tuple[int, int]:
        return int(sw * nx), int(sh * ny)

    def ring(nx: float, ny: float, radius: float, alpha: float,
             color=JADE, line=2):
        x, y = point(nx, ny)
        pulse_ring(draw, x, y, int(radius * scale), alpha, color,
                   max(1, int(line * scale)))

    if kind == "hero":
        # The sweep fades at both ends, so the loop closes cleanly.
        travel = smootherstep(phase)
        x = sw * (0.20 + 0.60 * travel)
        envelope = math.sin(math.pi * phase) ** 1.4
        add_sweep(
            overlay, x, int(sh * 0.12), int(sh * 0.91),
            22 * envelope, BRASS, half_width=max(12, sw // 85),
        )
        pulse = 10 + 3.2 * (0.5 + 0.5 * math.sin(math.tau * phase))
        ring(0.733, 0.505, pulse, 62 + 22 * math.sin(math.tau * phase), JADE, 2)
        ring(0.733, 0.505, pulse + 13, 22 + 10 * math.sin(math.tau * phase), BRASS, 1)

    elif kind in ("map", "work"):
        # Each project emblem receives a soft focus. Neighbouring states blend.
        if kind == "map":
            nodes = [(0.269, 0.461), (0.584, 0.461), (0.899, 0.461)]
            y_ratio = 0.461
        else:
            nodes = [(0.279, 0.481), (0.593, 0.481), (0.908, 0.481)]
            y_ratio = 0.481

        for index, (nx, ny) in enumerate(nodes):
            focus = cyclic_focus(phase, len(nodes), index)
            if focus < 0.025:
                continue
            color = PROJECT_ACCENTS[index]
            pulse = 0.5 + 0.5 * math.sin(math.tau * phase * 2 + index * 0.7)
            radius = (8 if kind == "map" else 7) + (3.5 if kind == "map" else 3) * pulse
            ring(nx, ny, radius, 82 * focus, color, 2)
            ring(nx, ny, radius + 8, 28 * focus, color, 1)

    elif kind == "process":
        nodes = [0.119, 0.306, 0.494, 0.681, 0.869]
        travel = ping_pong(phase)
        x_ratio = nodes[0] + (nodes[-1] - nodes[0]) * travel
        y_ratio = 0.45

        for index, nx in enumerate(nodes):
            distance = abs(x_ratio - nx)
            focus = 1.0 - smootherstep(distance / 0.15)
            if focus > 0.02:
                ring(nx, y_ratio, 20 + 3 * focus, 78 * focus,
                     PROCESS_ACCENTS[index], 2)

        x, y = point(x_ratio, y_ratio)
        r = 3.0 * scale
        draw.ellipse((x-r, y-r, x+r, y+r), fill=(*BRASS, 220))

    elif kind == "connect":
        centers = [0.149, 0.391, 0.632, 0.862]
        for index, nx in enumerate(centers):
            focus = cyclic_focus(phase, len(centers), index)
            if focus < 0.025:
                continue
            pulse = 0.5 + 0.5 * math.sin(math.tau * phase * 2 + index * 0.55)
            radius = 12 + 3 * pulse
            ring(nx, 0.61, radius, 72 * focus, CONTACT_ACCENTS[index], 2)
            ring(nx, 0.61, radius + 9, 22 * focus, CONTACT_ACCENTS[index], 1)

    elif kind == "signal":
        # A measured scan moves forward and back over the existing signal trace.
        travel = ping_pong(phase)
        x_ratio = 0.40 + 0.48 * travel
        y_ratio = 0.66 - 0.28 * travel + 0.018 * math.sin(math.tau * phase)
        x, y = point(x_ratio, y_ratio)
        pulse = 7 + 2 * (0.5 + 0.5 * math.sin(math.tau * phase))
        pulse_ring(draw, x, y, int(pulse * scale), 105, BLUE, 2 * scale)
        r = 2.7 * scale
        draw.ellipse((x-r, y-r, x+r, y+r), fill=(*BRASS, 220))

        sweep_x = sw * (0.34 + 0.58 * travel)
        sweep_strength = 14 + 5 * (0.5 + 0.5 * math.sin(math.tau * phase))
        add_sweep(
            overlay, sweep_x, int(sh * 0.28), int(sh * 0.78),
            sweep_strength, BLUE, half_width=max(10, sw // 100),
        )

    # Supersampling keeps the thin rings and glows clean at the final 800px width.
    return overlay.resize((width, height), Image.Resampling.LANCZOS)


def build_shared_palette(frames: list[Image.Image]) -> Image.Image:
    """Build one palette for the whole animation to prevent frame-to-frame color flicker."""
    sample_width = 128
    sample_height = max(1, round(frames[0].height * sample_width / frames[0].width))
    sheet = Image.new("RGB", (sample_width * len(frames), sample_height))
    for index, frame in enumerate(frames):
        thumb = frame.resize((sample_width, sample_height), Image.Resampling.BOX)
        sheet.paste(thumb, (index * sample_width, 0))
    return sheet.quantize(colors=GIF_COLORS, method=Image.Quantize.MEDIANCUT)


def make_gif(source_name: str, output_name: str, kind: str):
    source = ASSETS / source_name
    output = ASSETS / output_name
    base = render_source(source)
    rgb_frames = []

    for index in range(FRAMES):
        frame = base.convert("RGBA")
        frame.alpha_composite(overlay_for(kind, frame.size, index))
        rgb_frames.append(frame.convert("RGB"))

    palette = build_shared_palette(rgb_frames)
    frames = [
        frame.quantize(palette=palette, dither=Image.Dither.NONE)
        for frame in rgb_frames
    ]

    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=DURATION_MS,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(
        f"Created {output.relative_to(ROOT)} "
        f"({output.stat().st_size:,} bytes, {FRAMES} frames, "
        f"{FRAMES * DURATION_MS / 1000:.1f}s loop)"
    )


if __name__ == "__main__":
    for source_name, (output_name, kind) in SOURCES.items():
        make_gif(source_name, output_name, kind)
