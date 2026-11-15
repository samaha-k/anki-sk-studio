#!/usr/bin/env python3
"""Extract text from PDF / PPTX / DOCX / images into FILE.txt. Falls back to OCR for scanned pages.

  python3 extract_text.py FILE [FILE ...]

Typed slides and printed books extract well. Handwritten notes OCR badly: use the OCR text only to
find WHICH PAGE covers a topic, then look at that page image yourself (pdftoppm -f N -l N -r 100 -jpeg).
Needs: poppler-utils (pdftotext, pdftoppm), tesseract-ocr for OCR, python-pptx / python-docx for Office files.
"""
import os, subprocess, sys, tempfile, glob


def ocr_pdf(path):
    d = tempfile.mkdtemp(prefix="ocr_")
    subprocess.run(["pdftoppm", "-r", "150", "-gray", path, os.path.join(d, "p")], capture_output=True)
    out = []
    for img in sorted(glob.glob(os.path.join(d, "p-*.pgm"))):
        t = subprocess.run(["tesseract", img, "-"], capture_output=True, text=True, env=dict(os.environ, OMP_THREAD_LIMIT="1")).stdout
        out.append("=== PAGE %s\n%s" % (img.rsplit("-", 1)[1].split(".")[0], t))
    return "\n".join(out)


def extract(path):
    low = path.lower()
    txt = ""
    try:
        if low.endswith(".pdf") or open(path, "rb").read(4) == b"%PDF":
            txt = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True).stdout
            pages = int((subprocess.run(["pdfinfo", path], capture_output=True, text=True).stdout.split("Pages:")[-1].split()[0:1] or ["1"])[0])
            if len(txt.strip()) < 200 * max(1, pages) // 4:
                txt = ocr_pdf(path)
        elif low.endswith(".pptx"):
            from pptx import Presentation
            txt = "\n".join("=== SLIDE %d\n" % (i + 1) + "\n".join(sh.text_frame.text for sh in s.shapes if sh.has_text_frame)
                            for i, s in enumerate(Presentation(path).slides))
        elif low.endswith(".docx"):
            import docx
            txt = "\n".join(p.text for p in docx.Document(path).paragraphs)
        elif low.endswith((".jpg", ".jpeg", ".png")):
            txt = subprocess.run(["tesseract", path, "-"], capture_output=True, text=True).stdout
        elif low.endswith((".ppt", ".doc")):
            subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", os.path.dirname(path) or ".", path], capture_output=True)
            pdf = os.path.splitext(path)[0] + ".pdf"
            return extract(pdf) if os.path.exists(pdf) else 0
    except Exception as e:  # keep going on bad files
        txt = "EXTRACT ERROR: %s" % e
    open(path + ".txt", "w", encoding="utf-8").write(txt)
    return len(txt)


if __name__ == "__main__":
    for f in sys.argv[1:]:
        print("%7d  %s" % (extract(f), f))
