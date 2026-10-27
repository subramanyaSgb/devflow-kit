---
description: Write a code-grounded guidebook for ONE feature/module. Docs only; never changes code.
---

Produce (or update) `docs/guidebook/<name>.md` for the feature named in the argument.

1. **Discuss, grounded in code.** Trace the feature end-to-end (entry point → logic → data → UI/output),
   reading the real files. Note exact paths. List anything that looks wrong or stale.
2. **Fix issues with permission.** If you find a real defect, describe it and ask before changing code.
   This command's deliverable is the doc, not code changes.
3. **Write the guide** → `docs/guidebook/<name>.md`: what the feature is, how it works (with
   `path:line` references), inputs/outputs, configuration, edge cases, and how to verify it.
Keep it accurate to the current code — no aspirational claims.
