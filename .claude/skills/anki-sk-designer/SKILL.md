---
name: anki-sk-designer
description: Restyle any Anki deck (.apkg) into the SK card design. It adds a coloured subject band, a topic highlight, numbered self-test boxes, comparison tables, formula boxes, a memory-hook sticky note, a picture frame, dark mode and an SK footer, and keeps every card's wording, IDs and review progress. Use when someone asks to make their Anki cards look better, redesign, restyle or beautify a deck, or apply the SK design.
---

# SK card designer

Turns an existing Anki deck into the SK design **without changing a single word** and **without resetting progress**.

## What you need
- The deck exported from Anki: right-click the deck → Export → **Anki Deck Package (.apkg)**, with **Include media** ticked (and **Include scheduling** ticked if they want to keep their progress).
- Python 3 with `pip install anki` (the official Anki library), plus `pip install playwright && playwright install chromium` for previews.
- Tested end to end in Claude Code: export → design → delete → import kept every due date, interval and review.

## Steps
1. **Look first.** Unzip nothing by hand. Run the design on a copy and read the summary line: notes restyled, notes left alone (cloze or image occlusion stay as they are), subjects, tables and formula cards.
   ```bash
   python3 scripts/design.py INPUT.apkg OUTPUT.apkg --label "Pathology"
   ```
   - `--label` is the small text in the header band (the subject or course).
   - Add `--strict-formula` when the deck uses "=" to mean "is" (e.g. "HSIL = CIN 2 + 3"), so those points don't become formula boxes.
   - `--brand` sets the footer mark (default `SK`).
2. **Verify.** This must say PASS before you hand anything over.
   ```bash
   python3 scripts/verify.py INPUT.apkg OUTPUT.apkg --tables
   ```
   It checks: same notes, IDs and GUIDs; every word still there; card state unchanged; tags only gained `has_image` / `has_formula`; no missing pictures; footer on both sides.
3. **Read every comparison table** printed by `--tables`. A table that splits wrongly is worse than plain points. Typical mis-splits: a point that holds both items' labels ("BRCA1: …; BRCA2: …"), or a label that is an attribute ("Location:", "Types:"). For a wrong one, add the tag `no_table` to that note in the input deck and rebuild: it stays as points on every rebuild.
4. **Preview** a few cards at phone and desktop size, light and dark, and look at them:
   ```bash
   python3 scripts/preview.py OUTPUT.apkg previews --n 6 --phone --dark
   python3 scripts/preview.py OUTPUT.apkg previews_desk --n 6 --search "has_image"
   ```
5. **Hand over** with these import steps:
   1. Back up (File → Create Backup).
   2. Delete the old deck. The new note type replaces the old one, so importing over it would skip cards.
   3. File → Import the new .apkg, with **Import any learning progress** ticked, so reviews and due dates come back.
   4. Sync.

## How it reads a deck
| Shape | Example | Handling |
|---|---|---|
| Already split | fields `Question`, `Points`, `Hook`, … | restyled only |
| Front/Back with bullets | back `• point<br>• point<br>🔑 hook<br><img>`, front optionally `[UQ] … [extra]` | split into question, points, hook, picture; extra text after the hook goes to **📖 More detail** |
| Any Basic note | back with `<ul><li>`, numbered lines or plain lines | list items or lines become points; a line starting `🔑`, `Hook:` or `Mnemonic:` becomes the hook; pictures go to the frame |
| Cloze, image occlusion, or notes with more than one card (e.g. Basic and reversed) | n/a | left exactly as they are, so no card is lost |

Subjects come from the last part of the deck name (e.g. `Medicine::Cardiology` gives "Cardiology"), each with its own colour and icon. Badges come from tags and markers: `[UQ]` 🎓 University Q, `[HY]` ⚡ High-yield, tag `TermAsked` 🔥 Exam favourite, `[extra]` ✦ Bonus.

## Rules
- Never edit card wording or delete notes. If something looks wrong in the content, report it; don't fix it.
- Work on copies; never overwrite the user's original file.
- **Adding cards to a deck made with this designer:** use `--into THAT_DECK.apkg` with the same `--label`. The new cards share its note type and existing subjects keep their colours, so the result imports on top of the deck and progress is kept. Test this with `../anki-sk-cardbuilder/scripts/update_test.py`. `--into` refuses decks whose note type wasn't made by this designer.
- Don't invent a new look. The design lives in `assets/` (CSS, templates, JavaScript, icons); change it there only when the user asks.
