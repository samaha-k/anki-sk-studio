---
name: anki-sk-cardbuilder
description: Build exam-focused Anki flashcards from a student's own material (past papers, syllabus, lecture slides, notes, a Google Drive folder). It ranks topics by how often past papers ask them, writes lean cards in the student's sources' wording, checks for gaps, duplicates and errors, shows a preview to approve, and delivers a tested deck in the SK design. Use when a student asks to make, improve or update Anki cards for an exam or subject.
---

# SK card builder

Turns a student's own material into **lean, exam-targeted Anki cards**, then styles them with the `anki-sk-designer` skill.
The student studies from cards, so every card must be **correct, asked-for and in their teachers' wording**.

Read `references/card_rules.md` before writing cards, and `references/past_paper_analysis.md` before ranking topics.

## The workflow
Do the steps in order. Report briefly after each one, then carry on.

### 1. Gather
Ask once for:
- the exam date(s)
- the subjects
- past papers (with years)
- the syllabus
- slides and notes
- any existing Anki deck: Export → .apkg with **media and scheduling** ticked

For a public Google Drive folder: `python3 scripts/drive.py list <folder link>`, then `drive.py get tree.json dl --match "<pattern>"`.
- A private folder won't open; ask for "Anyone with the link", or uploads.
- `scripts/extract_text.py` reads PDF, PPTX and DOCX.
- Scanned and handwritten pages OCR badly. Use the OCR text only to **find the page**, then look at that page image.

### 2. Rank topics from past papers
Build the topic × year table described in `references/past_paper_analysis.md`, and mark **UQ** (asked), **HY** (high-yield, not asked) and **TermAsked** (this year's term papers).
- Term papers repeat heavily year to year. When this year's paper is missing, last year's same term is the best stand-in.
- Say which papers are missing.

### 3. Check the existing deck before writing anything
For each priority topic, read the actual cards, not keyword counts:
- **Gaps:** an asked angle with no card.
- **Weak cards:** a missing part (e.g. gross morphology), or more than 5 points.
- **Errors:** check facts against the **department's own slides first**, then notes, then textbook. Numbers, schedules and national programmes (e.g. vaccination schedules) differ by country and edition: use the slide's version.
- **Suspended cards** covering an asked topic should be unsuspended, not duplicated.

### 4. Write new cards, then run the duplicate check
- Write cards as `cards.json` (format in `scripts/build_cards.py`), following `references/card_rules.md`.
- Put `why` (which question or gap) and `from` (which source, which page) on every card.
- Run `python3 scripts/dupcheck.py EXISTING.apkg cards.json` and **read every listed front**. Drop new cards an existing card already answers.

### 5. Preview and approve
1. Build and style the cards (the designer scripts are in `../anki-sk-designer/scripts/`):
   - `build_cards.py cards.json new.apkg`
   - `design.py new.apkg new_sk.apkg --label <Subject> --into EXISTING_SK.apkg` (or without `--into` for a brand-new deck)
2. Render a preview PDF: `preview.py new_sk.apkg preview --n 99 --phone --pdf`.
3. Send it with a list of each card's *why* and *source*, plus any before → after fixes to existing cards.
4. Mark textbook-only facts **✦ Bonus** (`"extra": true`), and say so plainly.
5. Wait for "ok" or changes.

### 6. Deliver one tested file
- Keep **one master copy**; apply only approved changes.
- Run `python3 scripts/update_test.py CURRENT.apkg NEW.apkg`. It must PASS: progress, flags and suspensions kept, no duplicates, 0 missing pictures.
- Give exact import steps:
  1. Back up.
  2. File → Import (default options).
  3. Unsuspend with `tag:UNSUSPEND is:suspended` → Ctrl+J, if used.
  4. Sync.
- Card state (suspension) doesn't travel through an update import, so tell the user any unsuspends to do by hand, by tag.

### 7. Plan the study days
Count active cards per subject and make a day-by-day plan to the exam:
- about 85–90 cards a day, never more than 100
- one catch-up day per week
- the subject with the nearest paper first, with the hardest or most valuable subject running daily
- timed past papers in the last days; MCQ banks as timed practice, not cards

## Never
- Never invent facts or sources. If a source doesn't cover something, say "textbook" and mark it ✦ Bonus.
- Never trust keyword counts for coverage. "stone" matches "tombstone", and "PKD" can hide under "ADPKD". Read the fronts.
- Never change existing wording silently. Every change goes in the preview as before → after.
- Never publish or share the student's slides, notes or past papers. They belong to their institution.
