from pathlib import Path
from io import BytesIO
import math

import cairosvg
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FRAMES = 16
DURATION_MS = 150

# Keep the source SVGs. The GIFs are derived presentation files.
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


def render_source(svg_path: Path) -> Image.Image:
    png = cairosvg.svg2png(url=str(svg_path), output_width=800)
    return Image.open(BytesIO(png)).convert("RGB")


def pulse_ring(draw, x, y, radius, alpha, color=JADE, width=2):
    rgba = (*color, max(0, min(255, int(alpha))))
    draw.ellipse((x-radius, y-radius, x+radius, y+radius), outline=rgba, width=width)


def add_sweep(layer: Image.Image, x: float, y0: int, y1: int, strength: int = 30, color=JADE):
    width, _ = layer.size
    band = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(band)
    half = max(14, width // 55)
    d.rectangle((int(x-half), y0, int(x+half), y1), fill=(*color, strength))
    band = band.filter(ImageFilter.GaussianBlur(radius=max(8, width // 90)))
    layer.alpha_composite(band)


def overlay_for(kind: str, size, frame: int) -> Image.Image:
    width, height = size
    phase = frame / FRAMES
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    if kind == "hero":
        x = width * (0.48 + 0.43 * phase)
        add_sweep(overlay, x, int(height * .12), int(height * .91), 25, BRASS)
        cx, cy = int(width * .733), int(height * .505)
        pulse = 8 + 5 * (0.5 + 0.5 * math.sin(phase * math.tau))
        pulse_ring(draw, cx, cy, pulse, 90, JADE, 2)
        pulse_ring(draw, cx, cy, pulse + 12, 34, BRASS, 1)

    elif kind == "map":
        # These coordinates match the three project emblems in the source SVG.
        nodes = [(0.269, .461), (.584, .461), (.899, .461)]
        active = int((phase * 3) % 3)
        for index, (nx, ny) in enumerate(nodes):
            x, y = int(width * nx), int(height * ny)
            if index == active:
                color = PROJECT_ACCENTS[index]
                radius = 9 + int(5 * (0.5 + 0.5 * math.sin(phase * math.tau * 3)))
                pulse_ring(draw, x, y, radius, 125, color, 2)
                pulse_ring(draw, x, y, radius + 9, 42, color, 1)

    elif kind == "process":
        nodes = [.119, .306, .494, .681, .869]
        active = int((phase * 5) % 5)
        process_accents = (JADE, BRASS, BLUE, JADE, COPPER)
        for index, nx in enumerate(nodes):
            x, y = int(width * nx), int(height * .45)
            if index == active:
                radius = 20 + int(5 * (0.5 + 0.5 * math.sin(phase * math.tau * 5)))
                pulse_ring(draw, x, y, radius, 125, process_accents[index], 2)
        x = int(width * (.119 + .75 * phase))
        y = int(height * .45)
        draw.ellipse((x-3, y-3, x+3, y+3), fill=(*BRASS, 205))

    elif kind == "work":
        # Pulse the actual project emblems, not the text or empty card space.
        nodes = [(0.279, .481), (.593, .481), (.908, .481)]
        active = int((phase * 3) % 3)
        for index, (nx, ny) in enumerate(nodes):
            if index == active:
                x, y = int(width * nx), int(height * ny)
                color = PROJECT_ACCENTS[index]
                radius = 9 + int(4 * (0.5 + 0.5 * math.sin(phase * math.tau * 3)))
                pulse_ring(draw, x, y, radius, 120, color, 2)
                pulse_ring(draw, x, y, radius + 8, 38, color, 1)

    elif kind == "connect":
        # A quiet focus travels across the four contact cards.
        centers = [.13, .37, .61, .85]
        active = int((phase * 4) % 4)
        accents = ((225, 123, 176), (91, 190, 133), (104, 174, 225), BRASS)
        for index, nx in enumerate(centers):
            if index == active:
                x, y = int(width * nx), int(height * .53)
                radius = 13 + int(4 * (0.5 + 0.5 * math.sin(phase * math.tau * 4)))
                pulse_ring(draw, x, y, radius, 110, accents[index], 2)
                pulse_ring(draw, x, y, radius + 9, 35, accents[index], 1)

    elif kind == "signal":
        x = int(width * (.42 + .45 * phase))
        y = int(height * (.66 - .28 * phase + .025 * math.sin(phase * math.tau)))
        pulse_ring(draw, x, y, 7 + int(3 * math.sin(phase * math.tau) ** 2), 140, BLUE, 2)
        draw.ellipse((x-3, y-3, x+3, y+3), fill=(*BRASS, 220))
        add_sweep(overlay, int(width * (.35 + .55 * phase)), int(height * .28), int(height * .78), 18, BLUE)

    return overlay


def make_gif(source_name: str, output_name: str, kind: str):
    source = ASSETS / source_name
    output = ASSETS / output_name
    base = render_source(source)
    frames = []

    for index in range(FRAMES):
        frame = base.convert("RGBA")
        frame.alpha_composite(overlay_for(kind, frame.size, index))
        frames.append(frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=64))

    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=DURATION_MS,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"Created {output.relative_to(ROOT)} ({output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    for source_name, (output_name, kind) in SOURCES.items():
        make_gif(source_name, output_name, kind)
