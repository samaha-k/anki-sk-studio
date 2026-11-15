"""Text rules for the SK card design: topic highlight, comparison tables, formula points.

Python port of the original lib_text.R. Card wording is never changed: table cells are cut from the
original points, and topics are only used to highlight words that are already in the question.
"""
import re
import html as _html

VERBS = "give|state|list|calculate|name|explain|outline|describe|draw|compare|discuss|enumerate"


def _sub(pat, rep, s, flags=0):
    return re.sub(pat, rep, s, count=1, flags=flags)


def strip_tags(x):
    return re.sub(r"<[^>]+>", "", x or "")


def clean_topic(x):
    x = _sub(r"^(an?|the) ", "", x.strip(), re.I)
    x = _sub(
        r"(,|:|\?|\. | and (what|which|how|its|their|when|why|where|who|does|do|is|are|the|tell|of|" + VERBS +
        r")\b| (used to|using|for establishing|for each|which|who) .*| in (an? |the )?(child|children|adult|patient|newborn)s?\b"
        r"| in (the|an?) | with .*| after .*| on .*| seen .*| that .*| by .*| without .*| to prevent .*| needing .*"
        r"| (point|points|need|needs|defines|suggest|indicated|treated|managed|classified)\b).*$", "", x)
    x = _sub(r"^.*\bfindings in ", "", x)
    x = _sub(r"^(an?|the|suspected|choice for) ", "", x.strip(), re.I)
    x = _sub(r"[.?]$", "", x).strip()
    if x.count("(") > x.count(")"):
        x = _sub(r"\s*\([^()]*$", "", x).strip()
    x = _sub(r"^each ", "", x)
    return "" if re.match(r"^(which|what|how|why|when|where)\b", x, re.I) else x


def vs_items(q0, share=True):
    if re.match(r"^(How|Compare)\b", q0) or len(re.findall(r" vs\.? | versus ", q0)) != 1:
        return None
    parts = re.split(r":\s+", q0)
    seg = [p for p in parts if re.search(r" vs\.? | versus ", p)][0]
    seg = _sub(r"\s*\(table\)$", "", seg)
    m = re.match(r"^(?:.* of )?(.+?) (?:vs\.?|versus) (.+)$", seg)
    if not m:
        return None
    a = _sub(r"^(an?|the) ", "", m.group(1))
    b = _sub(r"^(an?|the) ", "", m.group(2))
    if share and " " not in a and " " in b and " " not in _sub(r"^\S+ ", "", b) and len(a) < 10:
        a = a + " " + _sub(r"^\S+ ", "", b)
    return [a, b]


def topic_of(q):
    q0 = _sub(r"\?\s*$", "", re.sub(r"<[^>]+>", " ", q).strip())

    def two(m):
        return clean_topic(m.group(1)) + "|" + clean_topic(m.group(2))

    v = vs_items(q0, share=False)
    if v:
        return "|".join(v)

    def one(m):
        t = clean_topic(m.group(1))
        if re.match(r"^(patient|child)$", t) and " with " in q0:
            return clean_topic(_sub(r".* with ", "", q0))
        if re.match(r"^(drugs?|pain|surgery|tests?|methods?|patient|child|operation)$", t):
            r = re.search(r" (?:in|after|before|for) (?:an? |the )?([^,?]+)", q0)
            return clean_topic(r.group(1)) if r else ""
        return t

    rules = [
        (r"^How (?:does|do) (.+?) differ from (.+)$", two),
        (r"^How do (.+?) and (?:of )?(.+?) differ$", two),
        (r"(?:distinguish|differentiate|tell) (.+?) from (.+)$", two),
        (r"^(?:Define|State) (.+?),? and (?!" + VERBS + r")(.+?)\.?$", two),
        (r"^(?:Define|State) (.+?)(?:,? and (?:" + VERBS + r") .*)?\.?$", one),
        (r"^What (?:is|are) (an? [^,]+?)(?:,| and (?:what|which|how)|$)", one),
        (r"^Why (?:is|are|does|do) (\S+)", one),
        (r"^How (?:is|are|can|should|does|do) (?!you )(?:an? |the )?(.+?) (?:be )?(?:[a-z]+ed|present|presents|change|done)\b", one),
        (r"^(?:What|Which)\b.*? (?:defines|predispose to|admitted with|(?:descend|arise)s? from|(?:child|patient) with) (?:an? |the )?(.+)$", one),
        (r"^Where does (?:an? )?(.+?) (?:from|push)\b", one),
        (r"(?:key facts|facts) about (?:the )?(.+)$", one),
        (r"^(?:Give|State|List|Write) (?:the )?formulas? (?:for|of) (?:the )?(.+)$", one),
        (r"^Compare (.+?) (?:and|with) (.+?)\.?$", two),
        (r"^(?:Describe|Classify|Categorise|List|Name|Enumerate|Outline|Explain|Discuss|Draw|Write|Identify|Give|State)\b.*? of (?:an? |the )?(.+?)\.?$", one),
        (r"^(?:How|What|Which|When|Why|Where)\b.* of (.+)$", one),
        (r"^How (?:do|would) you (?:manage|treat|diagnose|investigate|examine|test|assess|drain|perform|control|confirm|counsel) (?:an? |the )?(.+)$", one),
        (r"^What (?:[a-z]+ ){0,2}?(?:causes|triggers|predisposes to|follows|follow) (.+)$", one),
        (r"^What do(?:es)? (?:the )?(.+?) (?:types|indicate|show|mean|suggest)\b", one),
        (r"^What (?:is|are) (?!the )(.+?)(?:,| and |$)", one),
        (r"^(?:What|Which|When|How|Why)\b.*?(?:associated with|used in|used for|used to [a-z]+|done in|done for|done after|seen in|occurs? in|occurs? after|to drain|confirms?|causes?|treats?|assess(?:es)?|relieves?|elevates?|predicts?|corrects?|for) (?:an? |the )?(.+)$", one),
        (r"^Which ([a-z -]+?) (?:is|are|takes|take|can|corrects|descend)\b", one),
        (r"^Where (?:is|are) (?:the )?(.+?) (?:and|made|located)\b", one),
        (r"^When is (.+?) (?:needed|used|indicated|done)\b", one),
        (r"^What (?:is|are) the (.+)$", one),
        (r"^(?:Describe|Classify|Categorise|List|Name|Enumerate|Outline|Explain|Discuss|Draw|Write|Identify|Give|State) (?:the |a |an )?(.+?)\.?$", one),
        (r"^([^:]{2,70}):\s", one),
    ]
    for pat, fn in rules:
        m = re.search(pat, q0)
        if m:
            return fn(m)
    if not re.match(r"^(What|How|Which|Why|When|Where|Who)\b", q0) and len(q0.split(" ")) <= 5 and not re.search(r" of | for ", q0):
        return clean_topic(q0)
    m = re.search(r"^[A-Z][A-Za-z ()-]*? (?:of|for|in) (?:an? |the )?(.+)$", q0)
    return one(m) if m else ""


# ---------------------------------------------------------------- comparison tables
def esc(x):
    return x.replace("&", "&amp;").replace("<", "&lt;")


def cap1(x):
    return x[:1].upper() + x[1:]


def words(x):
    return [w for w in strip_tags(x).lower().split() if w]


def common_prefix(cells):
    w = [c.split(" ") for c in cells]
    k = 0
    while True:
        nx = {v[k] if len(v) > k + 1 else None for v in w}
        if len(nx) != 1 or None in nx or "<" in next(iter(nx)):
            break
        k += 1
    return " ".join(w[0][:k]) if k else ""


def _row(label, a, b, i):
    return ('<tr><th>%s</th><td class="cell" style="--i:%d"><div class="tx">%s</div></td>'
            '<td class="cell" style="--i:%d"><div class="tx">%s</div></td></tr>' % (label, 2 * i - 2, a, 2 * i - 1, b))


def _compare_v1(q, pts):
    none = {"html": "", "why": ""}
    q0 = _sub(r"\?\s*$", "", re.sub(r"<[^>]+>", " ", q).strip())
    if not re.search(r"differ|compar|\bvs\.?\b|versus|distinguish|differentiate", q0, re.I):
        return none
    ab = vs_items(q0)
    if ab is None:
        m = re.search(r"^How (?:does|do) (.+?) differ from (.+)$|^How do (.+?) and (?:of )?(.+?) differ$|(?:distinguish|differentiate) (.+?) from (.+)$|^(?:Compare )?(.+?) (?:vs\.?|versus) (.+)$|^Compare (.+?) (?:and|with) (.+?)\.?$", q0)
        if not m:
            return {"html": "", "why": "no two named items in question"}
        ab = [g for g in m.groups() if g]
        if len(ab) != 2:
            return {"html": "", "why": "no two named items"}
    A = _sub(r"^(an?|the|of the|of) ", "", ab[0])
    B = _sub(r"^(an?|the|of the|of) ", "", ab[1])
    if " " not in A and " " in B and q0.startswith("How do "):
        A = A + " " + _sub(r"^\S+ ", "", B)
    p = [_sub(r"^•\s*", "", x) for x in pts]
    wa = [w for w in words(A) if w not in words(B)]
    wb = [w for w in words(B) if w not in words(A)]
    # row mode: "Label: A-part; B-part"
    segs = [s for x in p for s in re.split(r"(?<=\.)\s+(?=[A-Z][A-Za-z ]{0,25}:)", x)]
    rows = [re.match(r"^([A-Z][^:;<]{0,30}):\s*([^;]+?);\s*([^;]+?)\.?$", s) for s in segs]
    if rows and all(rows):
        L = [r.group(2) for r in rows]
        R = [r.group(3) for r in rows]
        kl, kr = common_prefix(L), common_prefix(R)
        if kl and kr and kl.lower() != kr.lower():
            def strip_k(x, k):
                return re.sub("^" + re.escape(k) + r"\s*", "", x, count=1)

            def head(T, k):
                return cap1(T) if k.lower() in T.lower() else "%s (%s)" % (cap1(T), k)
            body = "".join(_row(r.group(1), strip_k(r.group(2), kl), strip_k(r.group(3), kr), i + 1) for i, r in enumerate(rows))
            return {"html": '<table class="cmp"><thead><tr><th></th><th>%s</th><th>%s</th></tr></thead><tbody>%s</tbody></table>' % (esc(head(A, kl)), esc(head(B, kr)), body), "why": "row table"}
    if not wa or not wb:
        return {"html": "", "why": "items share all their words - kept as points"}
    stop_w = {"of", "the", "a", "an", "and", "in", "from", "for", "to", "with", "study", "test"}

    def keys(T, w):
        w = [re.sub(r"[^a-z-]", "", x) for x in w]
        w = [x for x in w if x and x not in stop_w]
        ini = "".join(x[0] for x in words(T) if x not in stop_w)
        return w + [ini] if len(ini) >= 3 else w
    ka, kb = keys(A, wa), keys(B, wb)

    def stem(w):
        return w[:max(5, len(w) - 3)] if len(w) > 5 else w

    def plain(x):
        return _sub(r"^(an?|the) ", "", strip_tags(x).strip().lower())

    def starts_key(x, k):
        return any(plain(x).startswith(stem(w)) for w in k)
    segs2 = [s for x in p for s in re.split(r"(?<=\.)\s+(?=(?:<b>)?[A-Z][A-Za-z ]{0,25}:)", x)]
    rows2 = [re.match(r"^(?:<b>)?([A-Z][^:;<]{0,40})(?::</b>|</b>:|:)\s*(.+?)\.?$", s) for s in segs2]

    def drop_key(x, k):
        tok = x.split(" ")
        n = 0
        kw = set(k) | set(words(" ".join(k)))
        while n < min(3, len(tok) - 1) and "<" not in tok[n] and re.sub(r"[^a-z-]", "", tok[n].lower()) in kw:
            n += 1
        return _sub(r"^[—–-]\s*", "", " ".join(tok[n:]))
    cells = None
    if rows2 and all(rows2):
        cells = []
        for r in rows2:
            b = r.group(2)
            sc = b.count(";")
            c = None
            if sc == 1:
                lr = [t.strip() for t in b.split(";")]
                if starts_key(lr[0], ka) and not starts_key(lr[0], kb) and starts_key(lr[1], kb) and not starts_key(lr[1], ka):
                    c = (r.group(1), drop_key(lr[0], ka), drop_key(lr[1], kb))
            elif sc == 0 and b.count(" vs ") == 1:
                lr = [t.strip() for t in b.split(" vs ")]
                if not starts_key(lr[0], kb) and not starts_key(lr[1], ka):
                    c = (r.group(1), lr[0], lr[1])
            cells.append(c)
    if cells and all(cells):
        body = "".join(_row(c[0], c[1], c[2], i + 1) for i, c in enumerate(cells))
        return {"html": '<table class="cmp"><thead><tr><th></th><th>%s</th><th>%s</th></tr></thead><tbody>%s</tbody></table>' % (esc(cap1(A)), esc(cap1(B)), body), "why": "row table"}
    # grouped mode: each point is about A only or B only
    def side(x):
        xl = plain(x)
        sa, sb = starts_key(x, ka), starts_key(x, kb)
        ma = bool(re.search(r"\b" + re.escape(stem(wa[0])), xl))
        mb = bool(re.search(r"\b" + re.escape(stem(wb[0])), xl))
        return "A" if (sa and not sb and not mb) else "B" if (sb and not sa and not ma) else "?"
    sides = [side(x) for x in p]
    if "?" not in sides and {"A", "B"} <= set(sides):
        own = set(words(A)) | set(words(B)) | set(ka) | set(kb)

        def cellify(x, i):
            m = re.match(r"^(?:<b>)?([^:<]{1,40})(?::</b>|</b>:|:)\s*", x)
            if m and all(w in own for w in words(m.group(1))):
                x = x[len(m.group(0)):]
            return '<span class="cell" style="--i:%d"><span class="tx">%s</span></span>' % (i, x)
        ca = "".join(cellify(x, i) for i, (x, s) in enumerate(zip(p, sides)) if s == "A")
        cb = "".join(cellify(x, i) for i, (x, s) in enumerate(zip(p, sides)) if s == "B")
        return {"html": '<table class="cmp two"><thead><tr><th>%s</th><th>%s</th></tr></thead><tbody><tr><td>%s</td><td>%s</td></tr></tbody></table>' % (esc(cap1(A)), esc(cap1(B)), ca, cb), "why": "column table"}
    return {"html": "", "why": "points mix both items - kept as points"}


def compare_of(q, pts):
    """Original rules first; then three extra shapes (v2). Always review new tables (see verify.py --tables)."""
    r = _compare_v1(q, pts)
    if r["html"]:
        return r
    q0 = _sub(r"\?\s*$", "", re.sub(r"<[^>]+>", " ", q).strip())
    if not re.search(r"differ|compar|\bvs\.?\b|versus|distinguish|differentiate|contrast", q0, re.I):
        return r
    p = [_sub(r"^•\s*", "", x) for x in pts]
    n = len(p)
    if n < 2:
        return r
    lab_re = r"^\s*(?:<b>)?([A-Z][^:;<]{0,35}?)(?:</b>)?\s*(?::</b>|:)\s*(.*)$"

    def cell(x, i):
        return '<span class="cell" style="--i:%d"><span class="tx">%s</span></span>' % (i, x.strip())

    def full(x, i, k):
        return '<tr><td class="full" colspan="%d">%s</td></tr>' % (k, cell(x, i))

    def ok_left(bad):
        return len(bad) <= max(1, n // 3) and (n - len(bad)) >= 2
    qw = re.sub(r"[^A-Za-z0-9 ]", " ", q0).lower()

    def in_q(l):
        ws = [w for w in re.sub(r"[^A-Za-z0-9 ]", " ", l).lower().split() if w not in ("the", "a", "of", "and")]
        return bool(ws) and all(re.search(r"\b" + re.escape(w[:max(3, len(w) - 2)]), qw) for w in ws)

    def two_rows(pairs, heads):
        out, i = [], -1
        for j in range(n):
            if pairs[j]:
                i += 2
                out.append('<tr><td class="cell" style="--i:%d"><div class="tx">%s</div></td><td class="cell" style="--i:%d"><div class="tx">%s</div></td></tr>' % (i - 1, pairs[j][0], i, pairs[j][1]))
            else:
                i += 1
                out.append(full(p[j], i, 2))
        return '<table class="cmp"><thead><tr><th>%s</th><th>%s</th></tr></thead><tbody>%s</tbody></table>' % (esc(cap1(heads[0])), esc(cap1(heads[1])), "".join(out))
    # 1. label-pair rows: "OA: x; RA: y"
    pr = []
    for x in p:
        h = re.split(r";\s*", x)
        a = re.match(lab_re, h[0]) if len(h) == 2 else None
        b = re.match(lab_re, h[1][:1].upper() + h[1][1:]) if len(h) == 2 else None  # "...; right: ..." also counts
        if b:
            b = re.match(lab_re, h[1], re.I)
        pr.append((strip_tags(a.group(1)), strip_tags(b.group(1)), a.group(2), b.group(2)) if a and b else None)
    good = [j for j in range(n) if pr[j]]
    if len(good) >= 2:
        L1 = {pr[j][0] for j in good}
        L2 = {pr[j][1] for j in good}
        bad = [j for j in range(n) if j not in good]
        L1 = {x.lower() for x in L1}
        L2 = {x.lower() for x in L2}
        if len(L1) == 1 and len(L2) == 1 and next(iter(L1)) != next(iter(L2)) and ok_left(bad):
            return {"html": two_rows([(x[2], x[3]) if x else None for x in pr], [pr[good[0]][0], pr[good[0]][1]]), "why": "v2 label-pair rows"}
    # 2. labelled groups (2-3 items named in the question)
    lb = []
    for x in p:
        m = re.match(lab_re, x)
        lb.append((strip_tags(m.group(1)), m.group(2)) if m and in_q(strip_tags(m.group(1))) else None)
    good = [j for j in range(n) if lb[j]]
    if len(good) >= 2:
        labs = []
        for j in good:
            if lb[j][0].lower() not in labs:
                labs.append(lb[j][0].lower())
        bad = [j for j in range(n) if j not in good]
        if len(labs) in (2, 3) and ok_left(bad):
            cols = ["".join(cell(lb[j][1], j) for j in good if lb[j][0].lower() == l) for l in labs]
            heads = [next(lb[j][0] for j in good if lb[j][0].lower() == l) for l in labs]
            extra = "".join(full(p[j], j, len(labs)) for j in bad)
            cls = " two" if len(labs) == 2 else " three"
            return {"html": '<table class="cmp%s"><thead><tr>%s</tr></thead><tbody><tr>%s</tr>%s</tbody></table>' % (
                cls, "".join("<th>%s</th>" % esc(cap1(h)) for h in heads), "".join("<td>%s</td>" % c for c in cols), extra), "why": "v2 labelled groups"}
    # 3. unlabelled halves led by each item's word
    ab = vs_items(q0)
    if ab is None:
        m = re.match(r"(?:How (?:does|do) )?(.+?) (?:differ from|vs\.?|versus|and) (.+?)(?: differ)?$", _sub(r"^(Differentiate|Distinguish|Compare)\s+", "", q0))
        ab = [m.group(1), m.group(2)] if m else None
    if ab:
        k1 = _sub(r"^(an?|the) ", "", ab[0].strip()).split(" ")[0].lower()
        k2 = _sub(r"^(an?|the) ", "", ab[1].strip()).split(" ")[0].lower()

        def st(w):
            return w[:max(4, len(w) - 3)]
        if len(k1) >= 3 and len(k2) >= 3 and st(k1) != st(k2):
            hv = []
            for x in p:
                h = re.split(r";\s*", x)
                if len(h) == 2:
                    a = _sub(r"^(an?|the) ", "", strip_tags(h[0]).strip().lower())
                    b = _sub(r"^(an?|the) ", "", strip_tags(h[1]).strip().lower())
                    hv.append((h[0], h[1]) if a.startswith(st(k1)) and b.startswith(st(k2)) else None)
                else:
                    hv.append(None)
            good = [j for j in range(n) if hv[j]]
            bad = [j for j in range(n) if j not in good]
            if len(good) >= 2 and ok_left(bad):
                return {"html": two_rows(hv, [ab[0].strip(), ab[1].strip()]), "why": "v2 unlabelled halves"}
    return r


def formula_idx(pts, strict=False):
    """1-based indices of points that hold a formula."""
    out = []
    for i, x in enumerate(pts, 1):
        t = strip_tags(x)
        if not re.search(r"[A-Za-z0-9)]\s*=\s*\S", t):
            continue
        if strict:
            ok = re.search(r"\d\s*[+×÷*/]\s*\d|=[^;,]*\s[+×÷]\s|\s[+×÷]\s[^;,]*=", t)
        else:
            ok = re.search(r"[+×÷*/]|\d", t)
        if ok:
            out.append(i)
    return out


def table_words_ok(points, table_html):
    """True if every word in the table is present in the original points (no words invented)."""
    def sp(x):
        return _html.unescape(re.sub(r"<[^>]+>", " ", x)).lower()
    src = set(re.findall(r"\w+", sp(" ".join(points))))
    tab = set(re.findall(r"\w+", sp(re.sub(r"<thead>.*?</thead>", " ", table_html, flags=re.S))))
    return tab <= src
