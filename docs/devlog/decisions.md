# Decisions

## 1. Adopted devflow workflow — 2026-10-27

devflow-kit is built with the very methodology it packages: a committed `docs/devlog/` trail,
`/save-work` + `/continue-work` handoffs, and the Stop-hook guard. Rationale: dogfood the kit and
keep an auditable, test-evidenced record.

## 2. Delivered as a Claude Code plugin + bootstrap command — 2026-10-27

Chosen over a copy-a-template folder and over user-global config: install once, improve once, every
project benefits; versions cleanly; shareable later. Design: `docs/superpowers/specs/2026-10-27-devflow-methodology-kit-design.md`.

## 3. Guard makes a single git call; fails open on all inputs — 2026-10-27

During Task 2 review the guard's `main()` was hardened to fail open on non-object JSON stdin, and the
dead `git ls-files` call was dropped (the committed check needs only `git ls-tree -r HEAD`). Spec §3/§3.2
+ plan reconciled to "one git call". The guard is pure stdlib and can never wedge a session.

## 4. Doc commands shipped in v1; memory seeding best-effort; default trailer from session — 2026-10-27

Resolved open questions (spec §17): `document-feature`/`demo-guide` ship now; memory seeding is
best-effort-and-skip (CLAUDE.md + docs/devlog are the guaranteed source of truth); the init-workflow
default commit trailer falls back to the session's attribution, recorded editably in the contract block.
