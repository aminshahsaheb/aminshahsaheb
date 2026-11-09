from pathlib import Path
from io import BytesIO
import math

import cairosvg
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FRAMES = 12
DURATION_MS = 140

# Keep the source SVGs. The GIFs are derived presentation files.
SOURCES = {
    "profile-hero.svg": ("profile-hero.gif", "hero"),
    "profile-system-map.svg": ("profile-system-map.gif", "map"),
    "profile-operating-system.svg": ("profile-operating-system.gif", "process"),
    "profile-work-grid.svg": ("profile-work-grid.gif", "work"),
    "profile-signal.svg": ("profile-signal.gif", "signal"),
}

MINT = (151, 247, 194)


def render_source(svg_path: Path) -> Image.Image:
    png = cairosvg.svg2png(url=str(svg_path), output_width=800)
    return Image.open(BytesIO(png)).convert("RGB")


def pulse_ring(draw, x, y, radius, alpha, width=2):
    color = (*MINT, max(0, min(255, int(alpha))))
    draw.ellipse((x-radius, y-radius, x+radius, y+radius), outline=color, width=width)


def add_sweep(layer: Image.Image, x: float, y0: int, y1: int, strength: int = 30):
    width, _ = layer.size
    band = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(band)
    half = max(14, width // 55)
    d.rectangle((int(x-half), y0, int(x+half), y1), fill=(*MINT, strength))
    band = band.filter(ImageFilter.GaussianBlur(radius=max(8, width // 90)))
    layer.alpha_composite(band)


def overlay_for(kind: str, size, frame: int) -> Image.Image:
    width, height = size
    phase = frame / FRAMES
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    if kind == "hero":
        x = width * (0.48 + 0.43 * phase)
        add_sweep(overlay, x, int(height * .12), int(height * .91), 38)
        cx, cy = int(width * .733), int(height * .505)
        pulse = 8 + 6 * (0.5 + 0.5 * math.sin(phase * math.tau))
        pulse_ring(draw, cx, cy, pulse, 100, 2)
        pulse_ring(draw, cx, cy, pulse + 11, 38, 1)

    elif kind == "map":
        nodes = [(0.175, .59), (.5, .67), (.825, .59)]
        active = int((phase * 3) % 3)
        for index, (nx, ny) in enumerate(nodes):
            x, y = int(width * nx), int(height * ny)
            if index == active:
                radius = 7 + int(6 * (0.5 + 0.5 * math.sin(phase * math.tau * 3)))
                pulse_ring(draw, x, y, radius, 145, 2)
                pulse_ring(draw, x, y, radius + 8, 55, 1)
        x = int(width * (0.17 + .66 * phase))
        y = int(height * (.59 + .08 * math.sin(phase * math.tau)))
        draw.ellipse((x-3, y-3, x+3, y+3), fill=(*MINT, 190))

    elif kind == "process":
        nodes = [.119, .306, .494, .681, .869]
        active = int((phase * 5) % 5)
        for index, nx in enumerate(nodes):
            x, y = int(width * nx), int(height * .45)
            if index == active:
                radius = 21 + int(6 * (0.5 + 0.5 * math.sin(phase * math.tau * 5)))
                pulse_ring(draw, x, y, radius, 145, 3)
        x = int(width * (.119 + .75 * phase))
        y = int(height * .45)
        draw.ellipse((x-3, y-3, x+3, y+3), fill=(*MINT, 210))

    elif kind == "work":
        for index, center in enumerate((.185, .5, .815)):
            local = (phase + index / 3) % 1
            x = int(width * (center - .14 + .28 * local))
            y = int(height * .32)
            draw.line((x-12, y, x+12, y), fill=(*MINT, 175), width=2)
            if index == int((phase * 3) % 3):
                pulse_ring(draw, int(width * center), int(height * .58), 7, 75, 1)

    elif kind == "signal":
        x = int(width * (.42 + .45 * phase))
        y = int(height * (.66 - .28 * phase + .025 * math.sin(phase * math.tau)))
        pulse_ring(draw, x, y, 7 + int(3 * math.sin(phase * math.tau) ** 2), 150, 2)
        draw.ellipse((x-3, y-3, x+3, y+3), fill=(*MINT, 220))
        add_sweep(overlay, int(width * (.35 + .55 * phase)), int(height * .28), int(height * .78), 22)

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
