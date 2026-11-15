#!/usr/bin/env python3
"""Render cards of a deck to PNG screenshots (and optionally one PDF) to check how they look.

  python3 preview.py DECK.apkg OUTDIR [--n 6] [--search "has_image"] [--phone] [--dark] [--front] [--pdf]

Needs: pip install anki playwright && playwright install chromium
"""
import argparse, base64, os, shutil, tempfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck")
    ap.add_argument("outdir")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--search", default="")
    ap.add_argument("--phone", action="store_true")
    ap.add_argument("--dark", action="store_true")
    ap.add_argument("--front", action="store_true", help="question side instead of answer side")
    ap.add_argument("--pdf", action="store_true", help="also combine the screenshots into preview.pdf")
    a = ap.parse_args()
    from anki.collection import Collection, ImportAnkiPackageRequest, ImportAnkiPackageOptions
    from playwright.sync_api import sync_playwright
    out = os.path.abspath(a.outdir)
    os.makedirs(out, exist_ok=True)
    work = tempfile.mkdtemp(prefix="skpreview_")
    col = Collection(os.path.join(work, "c.anki2"))
    col.import_anki_package(ImportAnkiPackageRequest(package_path=os.path.abspath(a.deck), options=ImportAnkiPackageOptions(with_scheduling=True)))
    media = col.media.dir()
    pages = []
    for i, cid in enumerate(list(col.find_cards(a.search))[: a.n]):
        card = col.get_card(cid)
        body = card.question() if a.front else card.answer()
        cls = "card nightMode night_mode" if a.dark else "card"
        p = os.path.join(work, "p%03d.html" % i)
        with open(p, "w", encoding="utf-8") as f:
            f.write('<!doctype html><html><head><meta charset="utf-8"><base href="file://%s/">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1"><style>%s</style></head>'
                    '<body class="%s"><div id="qa">%s</div></body></html>' % (media, card.note_type()["css"], cls, body))
        pages.append(p)
    col.close()
    w, h = (390, 844) if a.phone else (1280, 800)
    shots = []
    with sync_playwright() as pw:
        try:
            b = pw.chromium.launch()
        except Exception:
            # fall back to any Chromium already on the machine (or set SK_CHROMIUM=/path/to/chrome)
            import glob
            cands = [os.environ.get("SK_CHROMIUM", "")] + glob.glob("/opt/pw-browsers/chromium*/chrome-linux*/chrome") +                 ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"]
            exe = next((c for c in cands if c and os.path.exists(c)), None)
            if not exe:
                raise SystemExit("No browser found: run  playwright install chromium")
            b = pw.chromium.launch(executable_path=exe)
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
        for i, p in enumerate(pages):
            pg.goto("file://" + p)
            pg.wait_for_timeout(900)
            s = os.path.join(out, "card_%02d.png" % (i + 1))
            pg.screenshot(path=s, full_page=True)
            shots.append(s)
        if a.pdf and shots:
            imgs = "".join('<img src="data:image/png;base64,%s" style="width:100%%;margin-bottom:12px;border:1px solid #ccc">'
                           % base64.b64encode(open(s, "rb").read()).decode() for s in shots)
            hp = os.path.join(work, "all.html")
            open(hp, "w").write("<html><body style='margin:0'>%s</body></html>" % imgs)
            pg.goto("file://" + hp)
            pg.pdf(path=os.path.join(out, "preview.pdf"), format="A4", print_background=True)
        b.close()
    shutil.rmtree(work, ignore_errors=True)
    print("rendered %d cards to %s" % (len(shots), out))


if __name__ == "__main__":
    main()
