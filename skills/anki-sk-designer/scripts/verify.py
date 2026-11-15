#!/usr/bin/env python3
"""Check a designed deck against the original.

  python3 verify.py ORIGINAL.apkg DESIGNED.apkg [--tables]

Checks: same notes (IDs and GUIDs), card state unchanged (deck, due, interval, queue, flags), every word of the
original still present (only layout changed), tags only gained has_image / has_formula, all pictures present.
--tables prints every comparison table as plain text so you can read them (a mis-split table is worse than points).
"""
import argparse, collections, os, re, sys, tempfile, html

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import textrules as T  # noqa: E402

LAYOUT = {"Subject", "Icon", "Topic", "Formula", "Compare", "Count", "Asked"}


def load(path):
    from anki.collection import Collection, ImportAnkiPackageRequest, ImportAnkiPackageOptions
    d = tempfile.mkdtemp(prefix="skverify_")
    c = Collection(os.path.join(d, "c.anki2"))
    c.import_anki_package(ImportAnkiPackageRequest(package_path=os.path.abspath(path), options=ImportAnkiPackageOptions(with_scheduling=True)))
    return c


def toks(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = re.sub(r"\[(UQ|HY|extra)\]|🔑|•", " ", s)
    c = collections.Counter(re.findall(r"\w+", s.lower()))
    for k in ("uq", "hy", "hook", "mnemonic"):
        c.pop(k, None)  # badge codes move from "[UQ]" in the question to the Source field
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("original")
    ap.add_argument("designed")
    ap.add_argument("--tables", action="store_true")
    a = ap.parse_args()
    o, n = load(a.original), load(a.designed)
    on = {o.get_note(i).guid: o.get_note(i) for i in o.find_notes("")}
    nn = {n.get_note(i).guid: n.get_note(i) for i in n.find_notes("")}
    same_ids = set(on) == set(nn) and all(on[g].id == nn[g].id for g in on)
    bad_words, bad_tags, bad_cards = [], [], []
    for g, x in on.items():
        y = nn.get(g)
        if not y:
            continue
        ox = toks(" ".join(x.fields))
        keys = y.keys()
        ny = toks(" ".join(y[k] for k in keys if k not in LAYOUT))
        if ox != ny:
            bad_words.append((T.strip_tags(x.fields[0])[:70], dict(ox - ny), dict(ny - ox)))
        extra = set(y.tags) - set(x.tags)
        if not (set(x.tags) <= set(y.tags) and extra <= {"has_image", "has_formula"}):
            bad_tags.append(T.strip_tags(x.fields[0])[:70])
        oc = sorted((c.ord, o.decks.name(c.did), c.due, c.ivl, c.queue, c.type, c.flags) for c in x.cards())
        nc = sorted((c.ord, n.decks.name(c.did), c.due, c.ivl, c.queue, c.type, c.flags) for c in y.cards())
        if oc != nc:
            bad_cards.append(T.strip_tags(x.fields[0])[:70])
    miss = n.media.check().missing
    mt = [m for m in n.models.all() if any(n.models.use_count(m) for _ in [0])]
    brand = all("class=\"brand\"" in t["qfmt"] and "class=\"brand\"" in t["afmt"] for m in mt if "SK Edition" in m["name"] for t in m["tmpls"])
    print("notes: %d / %d | IDs and GUIDs kept: %s" % (len(nn), len(on), same_ids))
    print("wording changed on %d notes | tags changed wrongly on %d | card state changed on %d" % (len(bad_words), len(bad_tags), len(bad_cards)))
    print("missing pictures: %d | brand mark on both sides: %s" % (len(miss), brand))
    for b in bad_words[:5]:
        print("  WORDING:", b)
    for b in bad_cards[:5]:
        print("  CARD STATE:", b)
    if a.tables:
        for g, y in nn.items():
            if "Compare" in y.keys() and y["Compare"]:
                print("\n##", T.strip_tags(y["Question"]))
                for row in re.findall(r"(?s)<tr>(.*?)</tr>", y["Compare"]):
                    cells = [re.sub(r"\s+", " ", T.strip_tags(c)).strip() for c in re.findall(r"(?s)<t[hd][^>]*>(.*?)</t[hd]>", row)]
                    print("   " + " || ".join(cells))
    ok = same_ids and not bad_words and not bad_tags and not bad_cards and not miss
    print("RESULT:", "PASS" if ok else "CHECK THE ITEMS ABOVE")
    o.close(); n.close()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
