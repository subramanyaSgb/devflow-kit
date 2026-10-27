<!-- devflow:begin dev-workflow v1 -->
## Dev workflow (devflow)

This project uses the **devflow** plugin. Session boundaries: `/devflow:save-work` before `/clear`,
`/devflow:continue-work` to resume. A Stop-hook guard enforces the committed devlog trail.

**Contract (read by save-work / continue-work — keep these current):**

- Commit trailer: `Co-Authored-By: Claude <noreply@anthropic.com>`  <!-- confirm -->
- Run commands: none
- Restart commands: none
- Test command: <fill in, e.g. `pytest -q`>
- Stateful resources: none
- Push policy: none
- Scratch ledger: `.superpowers/sdd/progress.md`
<!-- devflow:end dev-workflow -->
