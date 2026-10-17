---
description: Review uncommitted SendToMac changes for bugs, security, and scope (best-practice style).
argument-hint: [staged|branch|paths]
---

Review the current work like the engineer on call for SendToMac.

1. Determine scope from `$ARGUMENTS` or default to **uncommitted** changes (`git diff` + `git diff --staged`).
2. Read **callers and tests** affected, not only the diff (`site.py`, `menu_app.py`, `web/`, signing scripts).
3. Check: local-network security, filename/path traversal, pairing limits, privacy claims, macOS signing/DMG if touched.
4. For each finding: what breaks, how to fix, what happens if skipped. Rank must-fix vs nice-to-have.
5. End with a short test plan (`python3 site.py --self-test`, manual QR flow if relevant).

Keep the review proportional; do not rewrite unrelated code.
