#!/usr/bin/env python3
"""Turn any Anki deck (.apkg) into the SK card design.

  python3 design.py INPUT.apkg OUTPUT.apkg --label "Pathology" [--brand "SK"] [--strict-formula]

What it does
  * Keeps every note's ID and GUID, and every card's state (deck, due date, interval, flags, suspension),
    by changing the note type in place (Anki's own "change note type").
  * Keeps the wording: question, points, hook, pictures and tags. Only the layout changes.
  * Adds layout fields: subject band, topic highlight, formula boxes, comparison tables, "More detail".
  * Writes a report CSV next to the output for review (tables, formulas, topics, icons).

Supported note shapes
  1. Already split (fields Question, Points, Hook, ...): restyled only.
  2. Front/Back with "• point<br>…🔑 hook<br><img>" backs (optionally "[UQ]/[HY] … [extra]" fronts).
  3. Any other 2-field Basic note: points come from <li> items or lines; a line starting 🔑 / "Hook:" /
     "Mnemonic:" becomes the memory hook; pictures go to the picture frame.
  Cloze and image-occlusion notes are left exactly as they are (reported).
"""
import argparse, csv, html, json, os, re, shutil, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
sys.path.insert(0, HERE)
import textrules as T  # noqa: E402

FIELDS = ["Question", "Points", "Hook", "Diagram", "Subject", "Source", "Asked", "Extra",
          "Count", "Icon", "Topic", "Formula", "Compare", "More"]
PALETTE = ["#dc2626", "#2563eb", "#059669", "#d97706", "#7c3aed", "#db2777", "#0891b2", "#65a30d",
           "#ea580c", "#4f46e5", "#be123c", "#0d9488", "#9333ea", "#ca8a04", "#1d4ed8", "#16a34a",
           "#c026d3", "#0284c7", "#a16207", "#475569", "#e11d48", "#15803d", "#7c2d12", "#57534e"]
# subject icon by keyword in the subdeck name (first match), else "book"
SUBJECT_ICONS = [
    (r"heart|cardi|cvs", "p-heart"), (r"kidney|renal|urin", "p-kidney"), (r"lung|resp|chest", "lungs"),
    (r"brain|cns|neuro", "p-brain"), (r"liver|hepat", "p-liver"), (r"bone|joint|ortho|muscle", "p-bone"),
    (r"blood|haem|wbc", "blood"), (r"breast", "p-breast"), (r"skin|derm", "p-skin"), (r"git|stomach|gastro|bowel", "p-stomach"),
    (r"endo|thyroid", "p-thyroid"), (r"pancrea", "p-pancreas"), (r"gall", "p-gall"), (r"female|gyn|obs", "p-female"),
    (r"male|testi|prostat", "p-male"), (r"lymph|node", "p-nodes"), (r"eye|retina|cornea|lens|glaucoma", "Retina"),
    (r"ear", "s-midear"), (r"nose|nasal", "s-nose"), (r"sinus", "s-sinus"), (r"pharyn|throat", "s-pharynx"),
    (r"laryn|voice", "s-larynx"), (r"oral|mouth|saliv", "s-oral"), (r"oesoph|esoph", "s-oeso"),
    (r"pharma|drug|therap", "pill"), (r"micro|infect|communic", "infection"), (r"stat|epidem", "chart"),
    (r"surg", "surgery"), (r"paed|child|pediat", "child"), (r"psych|behav", "chat"), (r"environ|water", "water"),
]
# topic icons, matched on the QUESTION only, first match wins (merged from the ENT and Pathology configs)
ICON_RULES = [
    ("complic", r"complicat|sequel"), ("compare", r"\bvs\b|versus|differ|compar|distinguish"),
    ("tumour", r"carcinoma|cancer|tumou?r|neoplas|malignan|lymphoma|leuka?emia|sarcoma|adenoma|blastoma|myeloma|metasta|polyp|\bmass\b|\blump"),
    ("genetic", r"\bgenes?\b|genetic|mutation|chromosom|inherit|familial|translocation|oncogene"),
    ("immune", r"immun|antibod|hypersensitiv|autoimmun|transplant|rejection|vaccin"),
    ("bleed", r"bleed|haemorrhag|hemorrhag|epistaxis|haematoma"), ("trauma", r"fracture|trauma|injur"),
    ("infection", r"infect|tubercul|\btb\b|bacteri|viral|virus|abscess|sepsis|fung|parasit|pneumonia|organism"),
    ("inflame", r"[a-z]itis\b|inflamm"), ("vascular", r"atheroscl|aneurysm|infarct|isch(a)?em|thromb|embol|hypertens|vascul"),
    ("child", r"child|infant|neonat|congenital|newborn|paediatric|pediatric"),
    ("morph", r"morpholog|microscop|histolog|gross|appearance|biopsy|stain"),
    ("surgery", r"surg|operat|ectomy|otomy|plasty|incision|graft"),
    ("investig", r"investigat|diagnos|\btests?\b|x-ray|\bct\b|\bmri\b|imaging|marker|\blabs?\b|confirm"),
    ("treat", r"treat|manag|therap|\bdrugs?\b|antibiotic|prevent"),
    ("classify", r"classif|\btypes?\b|\bstages?\b|\bgrades?\b|categor"),
    ("cause", r"cause|aetiolog|etiolog|predispos|risk|pathogen|mechanism"),
    ("features", r"feature|symptom|\bsigns?\b|present|clinical|findings"),
]


def rd(name):
    with open(os.path.join(ASSETS, name), encoding="utf-8") as f:
        return f.read()


def has_text(x):
    return bool(re.sub(r"&nbsp;|\s", "", T.strip_tags(x)))


def lighten(hexc, f=0.28):
    v = [int(hexc[i:i + 2], 16) for i in (1, 3, 5)]
    v = [round(c + (255 - c) * f) for c in v]
    return "#%02x%02x%02x" % tuple(v)


def soft(hexc):
    v = [int(hexc[i:i + 2], 16) for i in (1, 3, 5)]
    return "rgba(%d,%d,%d,.15)" % tuple(v)


def icon_url(svg):
    s = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='1.9' "
         "stroke-linecap='round' stroke-linejoin='round'>" + svg + "</svg>")
    for a, b in (("%", "%25"), ("#", "%23"), ("<", "%3C"), (">", "%3E")):
        s = s.replace(a, b)
    return 'url("data:image/svg+xml,' + s + '")'


# ------------------------------------------------------------------ parsing source notes
def parse_split(f):
    """Shape 1: already-split fields. Keep values; recompute layout fields."""
    v = {k: f.get(k, "") for k in FIELDS}
    pts = re.findall(r"(?s)<li[^>]*>(.*?)</li>", v["Points"]) or [x for x in v["Points"].split("<br>") if x.strip()]
    v["Count"] = v["Count"] or str(len(pts))
    return v, pts


def parse_frontback(front, back):
    """Shapes 2 and 3."""
    v = {k: "" for k in FIELDS}
    m = re.match(r"^(?:\[(UQ|HY)\]\s*)?(.*?)\s*(\[extra\])?\s*$", front, re.S)
    if m and (m.group(1) or m.group(3)):
        v["Source"], v["Question"], v["Extra"] = m.group(1) or "", m.group(2), m.group(3) or ""
    else:
        v["Question"] = front
    lis = re.findall(r"(?s)<li[^>]*>(.*?)</li>", back)
    if lis:
        pts = lis
        rest = re.sub(r"(?s)<(ul|ol)[^>]*>.*?</\1>", "\n", back)
        lines = [x for x in re.split(r"<br\s*/?>|\n|</?div[^>]*>", rest) if x.strip()]
        v["Points"] = re.search(r"(?s)<(ul|ol)[^>]*>.*?</\1>", back).group(0)
    else:
        lines = [x for x in re.split(r"<br\s*/?>|\n|</?div[^>]*>", back) if x.strip()]
        pts, rest_lines = [], []
        bullet = any(re.match(r"^\s*(•|-|\*|\d+[.)])\s", T.strip_tags(x)) for x in lines)
        for x in lines:
            t = T.strip_tags(x).strip()
            if re.match(r"^(🔑|hook:|mnemonic:)", t, re.I) or re.match(r"^\s*<img", x) or (bullet and not re.match(r"^\s*(•|-|\*|\d+[.)])\s", t)):
                rest_lines.append(x)
            else:
                pts.append(x)
        if not pts and rest_lines:
            pts = [rest_lines.pop(0)]
        lines = rest_lines
        v["Points"] = "<br>".join(pts)
    hook, imgs, more = [], [], []
    for x in lines:
        t = T.strip_tags(x).strip()
        if re.match(r"^(🔑|hook:|mnemonic:)", t, re.I):
            hook.append(x)
        elif re.fullmatch(r"\s*(<img[^>]*>\s*)+", x):
            imgs.append(x.strip())
        elif has_text(x) or "<img" in x:
            more.append(x)
    # the 🔑 / "Hook:" marker is shown by the design's sticky note, so it is not repeated in the text
    v["Hook"] = "<br>".join(re.sub(r"^(\s*(?:<[^>]+>)*\s*)(?:🔑\s*|(?:hook|mnemonic)\s*:\s*)", r"\1", h, flags=re.I) for h in hook)
    v["Diagram"] = "".join(imgs)
    v["More"] = "<br>".join(more)
    v["Count"] = str(len(pts))
    return v, pts


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--label", required=True, help="deck label shown in the header band, e.g. 'Pathology'")
    ap.add_argument("--brand", default="SK", help="footer mark (default SK)")
    ap.add_argument("--brand-name", default="", help="optional text after the mark")
    ap.add_argument("--strict-formula", action="store_true", help="deck uses '=' to mean 'is'")
    ap.add_argument("--into", default="", help="an already-designed deck: reuse its note type so the output imports ON TOP of it (adds/updates cards, keeps progress)")
    a = ap.parse_args()

    from anki.collection import (Collection, ImportAnkiPackageRequest, ImportAnkiPackageOptions,
                                 ExportAnkiPackageOptions, NoteIdsLimit)
    from anki.models import ChangeNotetypeRequest

    work = tempfile.mkdtemp(prefix="skdesign_")
    col = Collection(os.path.join(work, "c.anki2"))
    col.import_anki_package(ImportAnkiPackageRequest(package_path=os.path.abspath(a.input),
                                                     options=ImportAnkiPackageOptions(with_scheduling=True)))
    icons = json.load(open(os.path.join(ASSETS, "icons.json")))
    nids = list(col.find_notes(""))
    base_subjects = set()
    old_colours = {}
    if a.into:
        col.import_anki_package(ImportAnkiPackageRequest(package_path=os.path.abspath(a.into), options=ImportAnkiPackageOptions(with_scheduling=True)))
        into_nt = col.models.by_name("%s SK Edition" % a.label)
        if not into_nt:
            sys.exit("--into deck has no note type called '%s SK Edition' (check --label)" % a.label)
        if [f["name"] for f in into_nt["flds"]] != FIELDS:
            sys.exit("--into deck's note type has different fields (not made by this designer); build a separate deck instead")
        into_ids = set(col.find_notes("")) - set(nids)
        old_colours = dict(re.findall(r'\.sv\[data-subj="([^"]+)"\] \{ --accent: (#[0-9a-f]{6})', into_nt["css"]))
        base_subjects = {col.get_note(i)["Subject"] for i in into_ids if "Subject" in col.get_note(i).keys()}
    skipped, plan = [], {}
    for nid in nids:
        n = col.get_note(nid)
        nt = n.note_type()
        names = [f["name"] for f in nt["flds"]]
        if nt.get("type") == 1 or "Image Occlusion" in nt["name"] or len(names) < 2 or len(nt["tmpls"]) != 1:
            # cloze, image occlusion and note types with more than one card (e.g. "Basic (and reversed card)")
            # are left exactly as they are, so no card is ever removed
            skipped.append(nid)
            continue
        f = dict(zip(names, n.fields))
        if "Question" in names and "Points" in names:
            v, pts = parse_split(f)
        else:
            v, pts = parse_frontback(n.fields[0], n.fields[1])
            extra = [x for x in n.fields[2:] if x.strip()]
            if extra:
                v["More"] = "<br>".join([v["More"]] + extra if v["More"] else extra)
        deck = col.decks.name(n.cards()[0].did)
        v["Subject"] = v["Subject"] or deck.split("::")[-1]
        tags = list(n.tags)
        if "TermAsked" in tags and not v["Asked"]:
            v["Asked"] = "TermAsked"
        plan[nid] = (v, pts, tags, nt["id"])

    subjects = sorted({p[0]["Subject"] for p in plan.values()} | base_subjects)
    colours = dict(old_colours)  # subjects already in an --into deck keep their colour
    free = [c for c in PALETTE if c not in colours.values()] or PALETTE
    for s in subjects:
        if s not in colours:
            colours[s] = free[len([x for x in colours if x not in old_colours]) % len(free)]

    def subj_icon(s):
        for pat, ic in SUBJECT_ICONS:
            if re.search(pat, s, re.I):
                return ic
        return "book" if "book" in icons else "classify"
    sicon = {s: subj_icon(s) for s in subjects}

    report = []
    for nid, (v, pts, tags, _) in plan.items():
        q = v["Question"]
        ql = T.strip_tags(q).lower()
        icon = v["Icon"] if v["Icon"] in icons else ""
        matched = "(kept)" if icon else ""
        if not icon:
            for k, pat in ICON_RULES:
                m = re.search(pat, ql)
                if m:
                    icon, matched = k, m.group(0)
                    break
        if not icon:
            icon, matched = sicon[v["Subject"]], "(subject icon)"
        v["Icon"] = icon
        v["Topic"] = v["Topic"] or T.topic_of(q)
        if not v["Formula"]:
            v["Formula"] = " ".join(map(str, T.formula_idx(pts, strict=a.strict_formula)))
        if "no_table" in tags:
            cmp = {"html": "", "why": "no_table tag"}
        else:
            cmp = {"html": v["Compare"], "why": "(kept)"} if v["Compare"] else T.compare_of(q, pts)
        if cmp["html"] and not T.table_words_ok(pts, cmp["html"]):
            cmp = {"html": "", "why": "table dropped: words not found in points"}
        v["Compare"] = cmp["html"]
        if v["Diagram"] or "<img" in v["More"]:
            tags.append("has_image")
        if v["Formula"]:
            tags.append("has_formula")
        report.append({"nid": nid, "subject": v["Subject"], "question": T.strip_tags(q)[:120], "icon": icon, "matched": matched,
                       "topic": v["Topic"], "table": cmp["why"], "formula": v["Formula"], "image": bool(v["Diagram"]), "more": bool(v["More"])})

    # ---- note type
    subj_css = "\n".join('.sv[data-subj="%s"] { --accent: %s; --accent2: %s; --soft: %s; }\n.sv[data-subj="%s"] .si { -webkit-mask-image: %s; mask-image: %s; }'
                         % (s, c, lighten(c), soft(c), s, icon_url(icons[sicon[s]]), icon_url(icons[sicon[s]])) for s, c in colours.items())
    icon_css = "\n".join(".sv .ic-%s { -webkit-mask-image: %s; mask-image: %s; }" % (k, icon_url(v), icon_url(v)) for k, v in icons.items())
    css = rd("style.css").replace("/*ICONS*/", icon_css + "\n.nightMode .sv, .night_mode .sv { --soft: rgba(255,255,255,.08); }\n" + subj_css)
    more_html = '{{#More}}<section class="more"><span class="lbl">📖 MORE DETAIL</span>{{More}}</section>{{/More}}'

    def tpl(name):
        t = rd(name).replace("%%LABEL%%", html.escape(a.label)).replace("%%BRAND%%", html.escape(a.brand_name))
        t = t.replace('<span class="mono">SK</span>', '<span class="mono">%s</span>' % html.escape(a.brand))
        if name == "back.html":
            t = t.replace("  </main>", "    " + more_html + "\n  </main>")
        return t.replace("/*SHARED_JS*/", rd("shared.js"))
    mm = col.models
    if a.into:
        nt = into_nt
        nt["css"] = css  # same note type ID; colours now cover old + new subjects
        mm.save(nt)
    else:
        nt = mm.new("%s SK Edition" % a.label)
        for fn in FIELDS:
            mm.add_field(nt, mm.new_field(fn))
        t = mm.new_template("SK Card")
        t["qfmt"], t["afmt"] = tpl("front.html"), tpl("back.html")
        mm.add_template(nt, t)
        nt["css"] = css
        mm.add(nt)
        nt = mm.by_name("%s SK Edition" % a.label)

    # ---- change note type in place (keeps IDs, GUIDs and card scheduling), then fill the fields
    by_old = {}
    for nid, p in plan.items():
        by_old.setdefault(p[3], []).append(nid)
    for old_id, ids in by_old.items():
        old = mm.get(old_id)
        info = mm.change_notetype_info(old_notetype_id=old_id, new_notetype_id=nt["id"])
        req = info.input
        req.note_ids.extend(ids)
        req.new_fields[:] = [0] + [-1] * (len(FIELDS) - 1)
        req.new_templates[:] = [0] if old["tmpls"] else []
        mm.change_notetype_of_notes(req)
    for nid, (v, pts, tags, _) in plan.items():
        n = col.get_note(nid)
        for k in FIELDS:
            n[k] = v[k]
        n.tags = sorted(set(tags))
        col.update_note(n)

    # parent deck description
    top = sorted({col.decks.name(col.get_note(nid).cards()[0].did).split("::")[0] for nid in plan})
    sw = " &nbsp; ".join('<span style="color:%s">■</span> %s' % (c, s) for s, c in colours.items())
    desc = rd("deck_desc.html").replace("<!--SWATCHES-->", sw).replace("<!--LABEL-->", html.escape(a.label))
    for name in top:
        d = col.decks.by_name(name)
        if d:
            d["desc"] = desc
            col.decks.save(d)

    out = os.path.abspath(a.output)
    col.export_anki_package(out_path=out, options=ExportAnkiPackageOptions(with_scheduling=True, with_deck_configs=True,
                                                                             with_media=True, legacy=True),
                            limit=NoteIdsLimit(note_ids=list(plan) + skipped))
    col.close()
    rep = re.sub(r"\.apkg$", "", out) + "_report.csv"
    with open(rep, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(report[0]))
        w.writeheader()
        w.writerows(report)
    shutil.rmtree(work, ignore_errors=True)
    tables = sum(1 for r in report if r["table"] not in ("", "(kept)") and not r["table"].startswith(("no ", "no_table", "items", "points", "table dropped")))
    print("built %s | notes restyled %d | left as they were (cloze/other) %d | subjects %d | new tables %d | formula cards %d | report %s"
          % (os.path.basename(out), len(plan), len(skipped), len(subjects), tables, sum(1 for r in report if r["formula"]), os.path.basename(rep)))


if __name__ == "__main__":
    main()
