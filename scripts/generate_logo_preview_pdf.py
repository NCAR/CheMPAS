#!/usr/bin/env python3
"""Build a 7-page portrait PDF preview of the CheMPAS-A logo set.

Pages:
  1-3. NCAR variants on white / ncar-light-gray / ncar-gray
  4-6. University of Arizona variants on white / arizona-warm-gray /
       arizona-cool-gray
  7.   NSF NCAR and U of A brand palettes side by side

Workflow:
  - cairosvg rasterizes each logo SVG into a PDF (vector, not pixel)
    next to the SVG sources in docs/_static/.
  - pdflatex compiles the tracked docs/_static/logo_preview.tex twice
    (so internal references settle).
  - Aux/log files are deleted; logo_preview.pdf and the per-logo
    PDFs remain. Both are gitignored — the SVGs and the .tex source
    are the tracked truth.

Run from any cwd:
    python scripts/generate_logo_preview_pdf.py
"""

import subprocess
from pathlib import Path

import cairosvg

STATIC = Path(__file__).resolve().parent.parent / "docs" / "_static"
SCHEMES = ("ncar_blue", "ncar_aqua", "arizona_blue", "arizona_red")


def svg_to_pdf(stem: str) -> None:
    src = STATIC / f"{stem}.svg"
    dst = STATIC / f"{stem}.pdf"
    cairosvg.svg2pdf(url=str(src), write_to=str(dst))


def main():
    tex_path = STATIC / "logo_preview.tex"
    if not tex_path.exists():
        raise FileNotFoundError(f"missing TeX source: {tex_path}")

    print("Rasterizing SVGs to PDF via cairosvg...")
    for scheme in SCHEMES:
        svg_to_pdf(f"logo_chempas_{scheme}")
        svg_to_pdf(f"logo_chempas_{scheme}_icon")

    print(f"Compiling {tex_path.name} with pdflatex (twice)...")
    for _ in range(2):
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode",
             "-halt-on-error", tex_path.name],
            cwd=STATIC, check=True,
            stdout=subprocess.DEVNULL)

    for ext in (".aux", ".log", ".out"):
        f = STATIC / f"logo_preview{ext}"
        if f.exists():
            f.unlink()

    print(f"Wrote {STATIC / 'logo_preview.pdf'}")


if __name__ == "__main__":
    main()
