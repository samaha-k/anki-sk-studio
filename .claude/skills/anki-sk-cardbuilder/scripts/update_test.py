#!/usr/bin/env python3
"""Prove that importing NEW.apkg over the user's current deck keeps their progress.

  python3 update_test.py CURRENT.apkg NEW.apkg

Imports CURRENT into a fresh Anki collection, simulates studying (a review, a red flag, a manual suspension),
imports NEW with Anki's default options, and reports: notes added / updated, duplicates, whether review state,
flag and suspension survived, and missing pictures. Never send an update file that has not passed this test.
"""
import argparse, os, tempfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("current")
    ap.add_argument("new")
    a = ap.parse_args()
    from anki.collection import Collection, ImportAnkiPackageRequest, ImportAnkiPackageOptions
    from anki.import_export_pb2 import ImportAnkiPackageUpdateCondition as UC
    p = os.path.join(tempfile.mkdtemp(), "c.anki2")
    t = Collection(p)
    t.import_anki_package(ImportAnkiPackageRequest(package_path=os.path.abspath(a.current), options=ImportAnkiPackageOptions(with_scheduling=True)))
    before = t.note_count()
    cids = list(t.find_cards("-is:suspended"))[:2]
    t.sched.set_due_date([cids[0]], "7")
    t.set_user_flag_for_cards(1, [cids[0]])
    t.sched.suspend_cards([cids[1]])
    due = t.get_card(cids[0]).due
    r = t.import_anki_package(ImportAnkiPackageRequest(package_path=os.path.abspath(a.new), options=ImportAnkiPackageOptions(
        update_notes=UC.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_IF_NEWER, update_notetypes=UC.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_IF_NEWER, with_scheduling=True)))
    t.close()
    t = Collection(p)
    c0, c1 = t.get_card(cids[0]), t.get_card(cids[1])
    res = {"notes before": before, "notes after": t.note_count(), "new": len(r.log.new), "updated": len(r.log.updated),
           "conflicts (note type changed)": len(r.log.conflicting) if hasattr(r.log, "conflicting") else "n/a",
           "review kept": c0.due == due, "flag kept": c0.user_flag() == 1, "suspension kept": c1.queue == -1,
           "missing pictures": len(t.media.check().missing)}
    t.close()
    for k, v in res.items():
        print("%-32s %s" % (k, v))
    ok = res["review kept"] and res["flag kept"] and res["suspension kept"] and res["missing pictures"] == 0
    print("RESULT:", "PASS" if ok else "FAIL: do not send this file")


if __name__ == "__main__":
    main()
