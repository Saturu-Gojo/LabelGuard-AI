"""Visual comparison engine: pixel differencing -> regions in PDF points; overlay rendering."""
import cv2, numpy as np
from . import pdf_processor, ruleset
S = pdf_processor.DPI / 72.0

def diff_regions(old_img, new_img, ignore_boxes=()):
    a, b = cv2.imread(old_img, 0), cv2.imread(new_img, 0)
    resized = a.shape != b.shape
    if resized: b = cv2.resize(b, (a.shape[1], a.shape[0]))
    for bx in ignore_boxes:
        x0, y0, x1, y1 = [int(v * S) for v in bx]; a[max(0, y0-4):y1+4, max(0, x0-4):x1+4] = 255; b[max(0, y0-4):y1+4, max(0, x0-4):x1+4] = 255
    d = cv2.GaussianBlur(cv2.absdiff(a, b), (5, 5), 0)
    mask = cv2.dilate(cv2.threshold(d, 40, 255, cv2.THRESH_BINARY)[1], cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25)))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if w * h > 400: regions.append([round(x / S, 1), round(y / S, 1), round((x + w) / S, 1), round((y + h) / S, 1)])
    return regions, resized

def overlay(img_path, boxes, out_path):
    """boxes: [(bbox_pts, (B,G,R), label)]"""
    im = cv2.imread(img_path)
    for bb, col, lab in boxes:
        x0, y0, x1, y1 = [int(v * S) for v in bb]
        cv2.rectangle(im, (x0 - 4, y0 - 4), (x1 + 4, y1 + 4), col, 3)
        if lab: cv2.putText(im, lab, (x0 - 4, max(14, y0 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 2)
    cv2.imwrite(out_path, im); return out_path
