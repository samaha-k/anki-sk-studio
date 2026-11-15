#!/usr/bin/env python3
"""Before adding new cards, list EVERY existing card on the same topic (suspended ones included).

  python3 dupcheck.py EXISTING.apkg cards.json [--deck "Final::Medicine"]

For each new card it extracts key terms from the question and prints all existing fronts that share them.
Read the list yourself: if an existing card already answers it, don't add the new card; if that existing card is
SUSPENDED, ask the user to unsuspend it instead. Keyword COUNTS alone mislead (e.g. "stone" matches "tombstone"):
always read the matching fronts.
"""
import argparse, json, os, re, tempfile

STOP = set("what are the of and in a an is how which with for to its their give list describe define causes cause "
           "features types type treatment management diagnosis investigations clinical vs versus differ between".split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("existing")
    ap.add_argument("cards")
    ap.add_argument("--deck", default="")
    a = ap.parse_args()
    from anki.collection import Collection, ImportAnkiPackageRequest, ImportAnkiPackageOptions
    col = Collection(os.path.join(tempfile.mkdtemp(), "c.anki2"))
    col.import_anki_package(ImportAnkiPackageRequest(package_path=os.path.abspath(a.existing), options=ImportAnkiPackageOptions(with_scheduling=True)))
    rows = []
    for nid in col.find_notes('"deck:%s*"' % a.deck if a.deck else ""):
        n = col.get_note(nid)
        q = re.sub(r"<[^>]+>", "", n.fields[0])
        susp = any(c.queue == -1 for c in n.cards())
        rows.append((q, susp))
    col.close()
    for c in json.load(open(a.cards, encoding="utf-8")):
        terms = [w for w in re.findall(r"[a-z][a-z0-9-]{3,}", c["question"].lower()) if w not in STOP]
        hits = [(q, s) for q, s in rows if any(re.search(r"\b" + re.escape(t[:max(5, len(t) - 2)]), q.lower()) for t in terms)]
        print("\n## NEW:", c["question"])
        print("   key terms:", ", ".join(terms))
        for q, s in hits:
            print("   %s %s" % ("[SUSPENDED]" if s else "           ", q[:110]))
        if not hits:
            print("   (no existing card shares these terms)")


if __name__ == "__main__":
    main()
