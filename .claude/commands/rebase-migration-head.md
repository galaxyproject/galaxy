Rebase a feature-branch Alembic migration to descend from the current upstream head.

## Context

Galaxy uses Alembic for database schema migrations with two branches:
- `gxy` (galaxy model) in `lib/galaxy/model/migrations/alembic/versions_gxy/`
- `tsi` (tool shed install) in `lib/galaxy/model/migrations/alembic/versions_tsi/`

Multiple heads occur after merging/rebasing upstream code that added its own migration from the
same parent as ours. Instead of creating a merge migration (empty file with tuple `down_revision`),
we re-parent our migration to descend from the upstream head — keeping the chain linear.

## Steps

1. **Detect heads** — run `sh scripts/run_alembic.sh heads` from the repo root. Report
   which branch(es) have multiple heads and list the revision IDs.

2. **Identify which migration is ours** — for each branch with multiple heads, read the
   migration files in the appropriate `versions_gxy/` or `versions_tsi/` directory. Determine:
   - Which migration belongs to this feature branch (check `git log --oneline --diff-filter=A`
     for the file, or check if the migration filename matches work on this branch)
   - Which migration came from upstream
   - Their common ancestor(s) via `down_revision` chains

3. **Check for conflicts** — read both migrations' `upgrade()` functions. If they modify the
   same table or column, flag the conflict to the user before proceeding. If they touch
   different tables, note that the rebase is safe.

4. **Re-parent our migration** — edit our migration file's `down_revision`:
   - If `down_revision` is a **string** (single parent): replace it with the upstream head's
     revision ID.
     ```python
     # Before
     down_revision = "shared_ancestor"
     # After
     down_revision = "upstream_head"
     ```
   - If `down_revision` is a **tuple** (already a merge): replace the shared ancestor entry
     in the tuple with the upstream head's revision ID. Keep other entries.
     ```python
     # Before
     down_revision = ("shared_ancestor", "other_parent")
     # After
     down_revision = ("upstream_head", "other_parent")
     ```

5. **Verify** — run `sh scripts/run_alembic.sh heads` again and confirm the branch now has
   exactly one head.

6. **Report** — show the user the modified file, the old and new `down_revision`, and
   confirm the chain is now linear (or still a valid merge with the corrected parent).

## Notes

- This is the preferred approach when rebasing feature branches — avoids empty merge migration files.
- The upstream head becomes the new parent; our migration stays at the tip.
- If there are 3+ heads, repeat: rebase one at a time, re-running `heads` after each.
- If both migrations are from this branch (rare), ask the user which one should be the parent.
- If `scripts/run_alembic.sh` isn't available, fall back to: `cd lib/galaxy/model/migrations && alembic heads`.
