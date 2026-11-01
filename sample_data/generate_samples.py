"""Generates fictional, clearly-marked TEST labels (V1 EO -> V2 Radiation) with intentional discrepancies."""
import json, os
import numpy as np, zxingcpp
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

HERE = os.path.dirname(os.path.abspath(__file__))
SYM = os.path.join(HERE, "symbols")
os.makedirs(SYM, exist_ok=True)

def gtin_check(d13):
    s = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(d13))
    return str((10 - s % 10) % 10)

def font(sz):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    return ImageFont.truetype(p, sz) if os.path.exists(p) else ImageFont.load_default()

def make_symbol(name, line1, line2):
    im = Image.new("L", (160, 100), 255); d = ImageDraw.Draw(im)
    d.rectangle([2, 2, 157, 97], outline=0, width=4)
    d.text((80, 32), line1, fill=0, font=font(26), anchor="mm")
    d.text((80, 70), line2, fill=0, font=font(30), anchor="mm")
    im.save(os.path.join(SYM, f"{name}.png"))

def make_logo():
    im = Image.new("L", (120, 60), 255); d = ImageDraw.Draw(im)
    d.ellipse([4, 4, 56, 56], fill=0); d.text((88, 30), "MC", fill=0, font=font(30), anchor="mm")
    im.save(os.path.join(SYM, "logo.png"))

def build_reference_symbols():
    make_symbol("sterile_eo", "STERILE", "EO")
    make_symbol("sterile_radiation", "STERILE", "R")
    make_symbol("sterile_steam", "STERILE", "ST")
    make_logo()

def udi_png(text):
    a = np.array(zxingcpp.write_barcode(zxingcpp.BarcodeFormat.DataMatrix, text, 240, 240))
    return Image.fromarray(a).convert("L")

def label(path, version, sterile_symbol, sterile_text, gtin, warning=True, logo_dx=0):
    c = canvas.Canvas(path, pagesize=(420, 595)); H = 595
    c.setFont("Helvetica", 7); c.drawString(20, H - 18, f"TEST DOCUMENT - FICTIONAL DATA - NOT A VALID MEDICAL LABEL ({version})")
    c.setFont("Helvetica-Bold", 22); c.drawString(30, H - 70, "Cardiac Stent")
    c.setFont("Helvetica", 11); c.drawString(30, H - 92, "REF: STENT101")
    c.drawImage(ImageReader(os.path.join(SYM, "logo.png")), 270 + logo_dx, H - 100, 90, 45)
    c.drawImage(ImageReader(os.path.join(SYM, sterile_symbol + ".png")), 30, H - 190, 96, 60)
    c.setFont("Helvetica", 10); c.drawString(140, H - 160, sterile_text)
    if warning:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(30, H - 230, "WARNING: Do not reuse. Do not use if package is damaged.")
    c.setFont("Helvetica", 10)
    c.drawString(30, H - 270, "Manufacturer: MediCore Devices Pvt. Ltd.")
    c.drawString(30, H - 285, "12 Industrial Area, Lucknow, India")
    c.drawImage(ImageReader(udi_png("01" + gtin)), 30, H - 420, 110, 110)
    c.setFont("Helvetica", 10); c.drawString(160, H - 350, f"UDI: (01) {gtin}")
    c.save()

if __name__ == "__main__":
    build_reference_symbols()
    g1 = "0081234567890"; g1 += gtin_check(g1)
    g2 = "0081234567899"; g2 += gtin_check(g2)
    label(os.path.join(HERE, "old_label.pdf"), "V1", "sterile_eo", "Sterilized using ethylene oxide", g1)
    label(os.path.join(HERE, "revised_label.pdf"), "V2", "sterile_radiation", "Sterilized using irradiation", g2, warning=False, logo_dx=18)
    json.dump({"product_id": "STENT101", "product_name": "Cardiac Stent", "market": "EU", "language": "English",
               "old_version": "V1", "new_version": "V2", "change_reason": "Sterilization update",
               "change_request": "Update the sterilization method from EO to Radiation. Keep UDI, product identification, manufacturer details, and safety warnings unchanged."},
              open(os.path.join(HERE, "change_request.json"), "w"), indent=2)
    print("generated", g1, g2)
