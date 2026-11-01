"""PDF intelligence: render pages, extract text blocks, symbols, barcodes -> structured elements."""
import hashlib, os
import cv2, fitz, numpy as np, zxingcpp
from . import ruleset

DPI = 150
SYMBOL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "sample_data", "symbols")

def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()

_lib_cache = {}
def symbol_library(lib_dir=SYMBOL_DIR):
    if lib_dir not in _lib_cache:
        lib = {}
        for fn in sorted(os.listdir(lib_dir)) if os.path.isdir(lib_dir) else []:
            if fn.endswith(".png"):
                lib[fn[:-4]] = cv2.resize(cv2.imread(os.path.join(lib_dir, fn), 0), (64, 64), interpolation=cv2.INTER_AREA)
        _lib_cache[lib_dir] = lib
    return _lib_cache[lib_dir]

def match_symbol(gray):
    q = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)
    best, score = None, -1.0
    for name, ref in symbol_library().items():
        s = float(cv2.matchTemplate(q, ref, cv2.TM_CCOEFF_NORMED)[0][0])
        if s > score: best, score = name, s
    return (best, score) if score >= ruleset.RULES["tolerances"]["symbol_match"] else ("unknown_symbol", score)

def render_pages(pdf_path, out_dir, prefix):
    os.makedirs(out_dir, exist_ok=True); paths = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            p = os.path.join(out_dir, f"{prefix}_p{i+1}.png")
            page.get_pixmap(dpi=DPI, alpha=False).save(p); paths.append(p)
    return paths

def _ocr_blocks(img_path, scale):
    """OCR fallback for scanned pages (Tesseract). Returns text blocks in PDF points."""
    import pytesseract
    d = pytesseract.image_to_data(cv2.imread(img_path), output_type=pytesseract.Output.DICT)
    lines = {}
    for i, t in enumerate(d["text"]):
        if t.strip() and float(d["conf"][i]) > 0:
            k = (d["block_num"][i], d["par_num"][i], d["line_num"][i]); lines.setdefault(k, []).append(i)
    out = []
    for idxs in lines.values():
        x0 = min(d["left"][i] for i in idxs); y0 = min(d["top"][i] for i in idxs)
        x1 = max(d["left"][i] + d["width"][i] for i in idxs); y1 = max(d["top"][i] + d["height"][i] for i in idxs)
        out.append({"text": " ".join(d["text"][i] for i in idxs), "bbox": [x0/scale, y0/scale, x1/scale, y1/scale],
                    "size": (y1 - y0) / scale, "confidence": float(np.mean([float(d["conf"][i]) for i in idxs])) / 100, "source": "ocr"})
    return out

def extract(pdf_path, out_dir, prefix):
    """Returns {"hash", "pages": [{"page","width","height","image","elements":[...]}]}"""
    imgs = render_pages(pdf_path, out_dir, prefix); scale = DPI / 72.0; pages = []
    with fitz.open(pdf_path) as doc:
        for pi, page in enumerate(doc):
            els = []
            blocks = []
            for b in page.get_text("dict")["blocks"]:
                if b["type"] != 0: continue
                txt = " ".join("".join(s["text"] for s in l["spans"]) for l in b["lines"]).strip()
                if not txt: continue
                size = max(s["size"] for l in b["lines"] for s in l["spans"])
                blocks.append({"text": txt, "bbox": [round(v, 1) for v in b["bbox"]], "size": size, "confidence": 1.0, "source": "embedded"})
            if not blocks:  # scanned page -> OCR
                try: blocks = _ocr_blocks(imgs[pi], scale)
                except Exception: blocks = []
            max_size = max([b["size"] for b in blocks], default=0)
            for b in blocks:
                els.append({"type": "text", "field": ruleset.classify_text(b["text"], b["size"] == max_size and b["size"] > 15),
                            "value": b["text"], "bbox": b["bbox"], "confidence": b["confidence"], "source": b["source"]})
            # barcodes from rendered page
            rgb = cv2.cvtColor(cv2.imread(imgs[pi]), cv2.COLOR_BGR2GRAY)
            bc_boxes = []
            for r in zxingcpp.read_barcodes(rgb):
                xs = [r.position.top_left.x, r.position.top_right.x, r.position.bottom_left.x, r.position.bottom_right.x]
                ys = [r.position.top_left.y, r.position.top_right.y, r.position.bottom_left.y, r.position.bottom_right.y]
                bb = [round(min(xs)/scale, 1), round(min(ys)/scale, 1), round(max(xs)/scale, 1), round(max(ys)/scale, 1)]
                bc_boxes.append(bb)
                els.append({"type": "barcode", "field": "udi", "value": r.text, "format": str(r.format).split(".")[-1],
                            "bbox": bb, "confidence": 1.0, "source": "barcode"})
            # embedded images -> symbols / logo
            for info in page.get_image_info(xrefs=True):
                bb = [round(v, 1) for v in info["bbox"]]
                if any(_overlap(bb, b) > 0.5 for b in bc_boxes) or not info.get("xref"): continue
                raw = np.frombuffer(doc.extract_image(info["xref"])["image"], np.uint8)
                gray = cv2.imdecode(raw, cv2.IMREAD_GRAYSCALE)
                if gray is None: continue
                name, score = match_symbol(gray)
                field = "sterilization_symbol" if name in ruleset.RULES["sterilization_symbols"] else ("logo" if name == "logo" else f"symbol:{name}")
                els.append({"type": "symbol", "field": field, "value": name, "bbox": bb, "confidence": round(score, 3), "source": "symbol_matcher"})
            pages.append({"page": pi + 1, "width": page.rect.width, "height": page.rect.height, "image": imgs[pi], "elements": els})
    return {"hash": file_hash(pdf_path), "pages": pages}

def _overlap(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    area = max(1e-6, (a[2] - a[0]) * (a[3] - a[1])); return ix * iy / area
