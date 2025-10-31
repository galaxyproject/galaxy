Post CI failure summary to PR as a comment.

**Usage:** `/summarize_ci_post [PR#] [additional message]`

**Arguments:**
- `PR#` (optional): Pull request number to comment on. If omitted, uses latest analyzed PR (via `database/pr_reviews/latest` symlink)
- `additional message` (optional): Extra text to add before the summary

**Steps:**

1. **Determine PR number:**
   - If `{{arg}}` provided, use that as PR#
   - Otherwise, check `database/pr_reviews/latest` symlink:
     - If exists: `readlink database/pr_reviews/latest` to get PR#
     - If not exists: show error "No PR# provided and no latest review found. Run /summarize_ci first."

2. **Check for summary file:**
   - Look for `database/pr_reviews/<PR#>/summary`
   - If not found, show error:
     ```
     Error: database/pr_reviews/<PR#>/summary not found
     Run /summarize_ci <PR#> first to generate summary
     ```

3. **Read summary:**
   - Read contents of `database/pr_reviews/<PR#>/summary`
   - This contains the markdown-formatted failure summary

4. **Build comment body:**
   - If additional message provided, add it at the top
   - Add summary from file
   - Add footer with instructions

4. **Post comment to PR:**
   ```bash
   gh pr comment <PR#> --repo galaxyproject/galaxy --body "$(cat <<'EOF'
   [additional message if provided]

   ## CI Failure Summary

   [contents of database/pr_reviews/<PR#>/summary]

   ---
   *Summary generated with [Claude Code](https://claude.com/claude-code)*
   EOF
   )"
   ```

5. **Output:**
   ```
   ✅ Posted summary to PR #21218
   https://github.com/galaxyproject/galaxy/pull/21218#issuecomment-xxxxx
   ```

**Examples:**

**Simple post with explicit PR#:**
```bash
/summarize_ci_post 21218
```

**Post using latest analyzed PR:**
```bash
/summarize_ci_post
```

**With additional message:**
```bash
/summarize_ci_post 21218 "These failures look like known transient issues. Re-running checks."
```

**Latest PR with message:**
```bash
/summarize_ci_post "Only transient failures - safe to re-run"
```

**Output:**
```
Reading summary from database/pr_reviews/21218/summary...
✅ Posted summary to PR #21218
https://github.com/galaxyproject/galaxy/pull/21218#issuecomment-1234567890
```

**Example comment posted:**
```markdown
These failures look like known transient issues. Re-running checks.

## CI Failure Summary

Found 2 failed workflow run(s)

Run 18975780470:
  - Playwright test results JSON (0.1 MB) ⚡

✅ **Known transient failures (2):**
  • test_history_sharing.py::test_sharing_private_history - Issue #12345
    From: Playwright test results JSON
    Duration: 00:01:30
  • test_tool_discovery.py::test_tool_discovery_landing - Issue #67890
    From: Integration test results JSON
    Duration: 00:00:54

❌ **New failures requiring investigation (0)**

Total: 2 transient, 0 new

---
*Summary generated with [Claude Code](https://claude.com/claude-code)*
```

**Common workflow:**
```bash
# Analyze PR
/summarize_ci 21218

# Review output, then post to PR
/summarize_ci_post 21218 "Only transient failures - safe to merge after re-run"
```

**Error Handling:**
- If `database/pr_reviews/<PR#>/summary` doesn't exist, prompt to run `/summarize_ci` first
- If PR# is invalid, show error
- If gh command fails (permissions, network), show error message
