#!/usr/bin/env python3
"""Build an Anki deck from a cards JSON file (the format the SK designer understands).

  python3 build_cards.py cards.json OUT.apkg [--media DIR]

cards.json: a list of objects
  {"deck": "Final::Medicine::Cardiology", "question": "...", "points": ["...", "..."], "hook": "...",
   "source": "UQ" | "HY", "asked": true, "extra": false, "image": "ecg.png", "tags": ["Med_Cardio"],
   "why": "Asked Prof 2024 Q3", "from": "Cardiology slides p.12"}
GUIDs are stable (deck + question), so rebuilding the same card updates it in Anki instead of duplicating it.
Then style it:  python3 ../../anki-sk-designer/scripts/design.py OUT.apkg OUT_SK.apkg --label "Medicine"
"""
import argparse, hashlib, json, os, sys


def guid_for(*parts):
    h = hashlib.sha1("|".join(p.strip().lower() for p in parts).encode()).hexdigest()
    return "sk" + h[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cards")
    ap.add_argument("out")
    ap.add_argument("--media", default="")
    a = ap.parse_args()
    from anki.collection import Collection, ExportAnkiPackageOptions, NoteIdsLimit
    import tempfile
    cards = json.load(open(a.cards, encoding="utf-8"))
    d = tempfile.mkdtemp(prefix="skbuild_")
    col = Collection(os.path.join(d, "c.anki2"))
    m = col.models.by_name("Basic")
    ids, problems = [], []
    for i, c in enumerate(cards, 1):
        pts = c.get("points", [])
        if not c.get("question") or not pts:
            problems.append("card %d: needs a question and at least one point" % i)
            continue
        if len(pts) > 6:
            problems.append("card %d has %d points; split it (aim for 1-5)" % (i, len(pts)))
        front = ("[%s] " % c["source"] if c.get("source") else "") + c["question"] + (" [extra]" if c.get("extra") else "")
        back = "<br>".join("• " + p for p in pts)
        if c.get("hook"):
            back += "<br>🔑 " + c["hook"]
        if c.get("image"):
            back += '<br><img src="%s">' % c["image"]
            if a.media:
                col.media.add_file(os.path.join(a.media, c["image"]))
        n = col.new_note(m)
        n["Front"], n["Back"] = front, back
        n.guid = guid_for(c["deck"], c["question"])
        n.tags = list(c.get("tags", [])) + (["TermAsked"] if c.get("asked") else []) + ([c["source"]] if c.get("source") else [])
        col.add_note(n, col.decks.id(c["deck"]))
        ids.append(n.id)
    col.export_anki_package(out_path=os.path.abspath(a.out),
                            options=ExportAnkiPackageOptions(with_scheduling=False, with_deck_configs=False, with_media=True, legacy=True),
                            limit=NoteIdsLimit(note_ids=ids))
    col.close()
    print("built %s with %d cards" % (a.out, len(ids)))
    for p in problems:
        print("  CHECK:", p)


if __name__ == "__main__":
    main()
