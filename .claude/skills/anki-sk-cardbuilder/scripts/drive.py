#!/usr/bin/env python3
"""List and download a PUBLIC Google Drive folder ("Anyone with the link"), then extract text.

  python3 drive.py list FOLDER_URL_OR_ID [--out tree.json]
  python3 drive.py get tree.json OUTDIR --match "Past paper|Viva"      # download matching files + extract text

Private folders will not work: ask the user to share as "Anyone with the link", or to upload the files.
"""
import argparse, html, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def folder_id(x):
    m = re.search(r"folders/([A-Za-z0-9_-]+)", x)
    return m.group(1) if m else x


def ls(fid):
    h = subprocess.run(["curl", "-sSL", "-m", "60", "https://drive.google.com/embeddedfolderview?id=" + fid], capture_output=True, text=True).stdout
    return [(i, html.unescape(t), "folders" in u) for i, u, t in re.findall(r'id="entry-([^"]+)".*?<a href="([^"]+)".*?flip-entry-title">([^<]+)', h, re.S)]


def walk(fid, path="", depth=0, out=None):
    out = [] if out is None else out
    for i, t, isdir in ls(fid):
        p = path + "/" + t
        out.append({"path": p, "id": i, "folder": isdir})
        if isdir and depth < 6:
            walk(i, p, depth + 1, out)
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("list"); a1.add_argument("folder"); a1.add_argument("--out", default="drive_tree.json")
    a2 = sub.add_parser("get"); a2.add_argument("tree"); a2.add_argument("outdir"); a2.add_argument("--match", required=True)
    a = ap.parse_args()
    if a.cmd == "list":
        tree = walk(folder_id(a.folder))
        json.dump(tree, open(a.out, "w"), indent=1)
        for e in tree:
            print(("D " if e["folder"] else "  ") + e["path"])
        print("%d entries, %d files -> %s" % (len(tree), sum(not e["folder"] for e in tree), a.out))
    else:
        from extract_text import extract
        os.makedirs(a.outdir, exist_ok=True)
        for e in json.load(open(a.tree)):
            if e["folder"] or not re.search(a.match, e["path"], re.I):
                continue
            name = re.sub(r"[^\w.-]+", "_", e["path"].strip("/"))[-90:]
            dst = os.path.join(a.outdir, name)
            subprocess.run(["curl", "-sSL", "-m", "300", "-o", dst, "https://drive.google.com/uc?export=download&id=" + e["id"]])
            if open(dst, "rb").read(15).lower().startswith(b"<!doctype html") or open(dst, "rb").read(6) == b"<html ":
                # Google Docs files: try the text export instead
                subprocess.run(["curl", "-sSL", "-m", "120", "-o", dst + ".txt", "https://docs.google.com/document/d/%s/export?format=txt" % e["id"]])
                print("doc  ", e["path"])
                continue
            n = extract(dst)
            print("%6d chars  %s" % (n, e["path"]))


if __name__ == "__main__":
    main()
