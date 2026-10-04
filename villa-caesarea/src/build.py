"""Build all sheets → SVG/HTML → PDF (+ PNG previews).

usage: python3 build.py [sheet numbers...] [--png] [--nopdf]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")
sys.path.insert(0, HERE)

import sheets as S  # noqa: E402

FONT_CSS = "".join(
    f"@font-face{{font-family:'{fam}';src:url('file://{ROOT}/fonts/{f}') format('truetype');font-weight:{wt};}}"
    for fam, f, wt in [("Heebo", "Heebo-300.ttf", 300), ("Heebo", "Heebo-400.ttf", 400), ("Heebo", "Heebo-500.ttf", 500),
                       ("Heebo", "Heebo-500.ttf", 600), ("Heebo", "Heebo-700.ttf", 700), ("Heebo", "Heebo-800.ttf", 800),
                       ("Frank Ruhl Libre", "Frank-300.ttf", 300), ("Frank Ruhl Libre", "Frank-500.ttf", 500),
                       ("Frank Ruhl Libre", "Frank-700.ttf", 700)])


def page_html(svg):
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{FONT_CSS}"
            f"@page{{size:{S.W}mm {S.H}mm;margin:0}}html,body{{margin:0;padding:0}}"
            f"svg{{display:block}}</style></head><body>{svg}</body></html>")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    want = {int(a) for a in args} if args else None
    os.makedirs(os.path.join(OUT, "sheets"), exist_ok=True)
    jobs = []
    for (no, title, scale, fn) in S.SHEETS:
        if want and no not in want:
            continue
        sh, ok = S.build_sheet(no, title, scale, fn)
        p = os.path.join(OUT, "sheets", f"sheet_{no:02d}.html")
        with open(p, "w", encoding="utf-8") as f:
            f.write(page_html(sh.svg()))
        jobs.append(dict(no=no, html=p, pdf=p.replace(".html", ".pdf"), png=os.path.join(OUT, "png", f"sheet_{no:02d}.png")))
        print(f"sheet {no:02d} {'ok' if ok else 'PLACEHOLDER'}  {title}")
    js = os.path.join(HERE, "render_pages.js")
    cfg = dict(jobs=jobs, png="--png" in flags, pdf="--nopdf" not in flags, w=S.W, h=S.H)
    subprocess.run(["node", js, json.dumps(cfg)], check=True)
    if "--nopdf" not in flags and not want:
        from pypdf import PdfWriter
        wr = PdfWriter()
        for j in jobs:
            wr.append(j["pdf"])
        dst = os.path.join(OUT, "Beit_Kurkar_Final_Project.pdf")
        wr.write(dst)
        print("PDF:", dst)


if __name__ == "__main__":
    main()
