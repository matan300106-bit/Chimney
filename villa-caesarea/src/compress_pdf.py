"""Recompress raster images inside sheet PDFs (Chromium rasterises some hatch fills)."""
import io
import sys

import pikepdf
from PIL import Image


def compress(src, dst, quality=82, max_px=2400):
    pdf = pikepdf.open(src)
    for page in pdf.pages:
        seen = set()
        def walk(res):
            xo = res.get("/XObject", {}) if res is not None else {}
            for k, o in list(xo.items()):
                yield o
            pats = res.get("/Pattern", {}) if res is not None else {}
            for k, p in list(pats.items()):
                r2 = p.get("/Resources")
                if r2 is not None:
                    yield from walk(r2)
        for o in walk(page.Resources):
            if o.objgen in seen or o.get("/Subtype") != "/Image":
                continue
            seen.add(o.objgen)
            try:
                pim = pikepdf.PdfImage(o)
                img = pim.as_pil_image()
            except Exception:
                continue
            if len(o.read_raw_bytes()) < 20000:
                continue
            smask = o.get("/SMask")
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            if max(img.size) > max_px:
                img.thumbnail((max_px, max_px))
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=quality, optimize=True)
            o.write(buf.getvalue(), filter=pikepdf.Name.DCTDecode)
            o.ColorSpace = pikepdf.Name.DeviceRGB if img.mode == "RGB" else pikepdf.Name.DeviceGray
            o.BitsPerComponent = 8
            o.Width, o.Height = img.size
            for key in ("/DecodeParms", "/Decode"):
                if key in o:
                    del o[key]
            if smask is not None:
                o.SMask = smask
    # de-duplicate identical image streams
    import hashlib
    canon = {}
    remap = {}
    for o in pdf.objects:
        if isinstance(o, pikepdf.Stream) and o.get("/Subtype") == "/Image":
            h = hashlib.md5(o.read_raw_bytes() + repr(o.get("/SMask") is not None).encode()).hexdigest()
            sm = o.get("/SMask")
            if sm is not None:
                h += hashlib.md5(sm.read_raw_bytes()).hexdigest()
            if h in canon:
                remap[o.objgen] = canon[h]
            else:
                canon[h] = o
    for o in pdf.objects:
        if isinstance(o, (pikepdf.Dictionary, pikepdf.Stream)):
            cands = [o.get("/XObject")]
            res = o.get("/Resources")
            if isinstance(res, pikepdf.Dictionary):
                cands.append(res.get("/XObject"))
            for xo in cands:
                if not isinstance(xo, pikepdf.Dictionary):
                    continue
                for k in list(xo.keys()):
                    v = xo[k]
                    if hasattr(v, "objgen") and v.objgen in remap:
                        xo[k] = remap[v.objgen]
    pdf.remove_unreferenced_resources()
    pdf.save(dst, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)


if __name__ == "__main__":
    compress(sys.argv[1], sys.argv[2])
