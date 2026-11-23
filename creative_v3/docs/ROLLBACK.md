# Creative Stickman Studio V3 — Rollback Procedure

Creative Stickman Studio V3 is isolated inside `creative_v3/` and `third_party/` on branch `feature/creative-stickman-v3`, with zero modifications to legacy `core/`, `production_engine/`, or `studio_ui/` entrypoints.

## Option 1: Disable V3 Without Losing Files
- Ensure `CREATIVE_V3_ENABLED` remains unset / `0` (default OFF).
- Legacy pipelines (`core/orchestration/orchestrator.py`, `production_engine/`) continue to run unchanged.

## Option 2: Switch Back to `main` or Backup Tag
```powershell
git checkout main
# Or inspect exact pre-V3 commit:
git show backup/pre-creative-v3
```

## Option 3: Remove Untracked V3 Artifacts Only
If you want to remove V3 directories after switching back to `main`:
```powershell
Remove-Item -Recurse -Force creative_v3, third_party
```
Do **NOT** run `git reset --hard` or `git clean -fd` because pre-existing project working-tree edits exist on `main`.
