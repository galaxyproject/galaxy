Analyze CI failures for PR {{arg}} in galaxyproject/galaxy repository.

Steps:
1. **Backup existing review directory if it exists**:
   - Check if `database/pr_reviews/{{arg}}/` exists
   - If yes, move to `database/pr_reviews/{{arg}}_backup_$(date +%Y%m%d_%H%M%S)`
   - Notify user: "Backed up previous review to {{arg}}_backup_YYYYMMDD_HHMMSS"
2. **Create fresh review directory**: `mkdir -p database/pr_reviews/{{arg}}`
3. Get PR head commit SHA: `gh pr view {{arg}} --repo galaxyproject/galaxy --json headRefOid --jq .headRefOid`
4. Find failed workflow runs: `gh api repos/galaxyproject/galaxy/commits/<SHA>/check-runs --jq '.check_runs[] | select(.conclusion == "failure") | .html_url' | grep -oE 'runs/[0-9]+' | cut -d'/' -f2 | sort -u`
   - **If no failed runs found:** Check if tests are still in progress
   - If in progress: Report "Tests still running - wait for completion"
   - If all passed: Report "No failures - all tests passed!" and exit
5. For each failed run, list artifacts: `gh api repos/galaxyproject/galaxy/actions/runs/<RUN_ID>/artifacts --jq '.artifacts[] | {name: .name, id: .id, size_in_bytes: .size_in_bytes}'`
   - **If run has no artifacts:** Report "Run <RUN_ID> has no artifacts - may be too old (artifacts expire after 90 days)"
6. **Download all test artifacts to review directory**:
   - Prefer JSON artifacts (e.g., "Playwright test results JSON", "Integration test results JSON")
   - Download to `database/pr_reviews/{{arg}}/`
   - Command: `gh run download <RUN_ID> --dir database/pr_reviews/{{arg}}/ --repo galaxyproject/galaxy`
   - This preserves artifact directory structure (e.g., "Playwright test results JSON/run_playwright_tests.json")
   - Multiple test types/shards will have different artifact names, avoiding collisions
   - **CRITICAL: Check exit code after each download**
   - **If download fails:**
     - Show error message with run ID
     - Ask user: "Download failed for run <RUN_ID>. This may be due to network timeout or expired artifacts. Retry? (y/n)"
     - If yes, retry with longer timeout (300s)
     - If no or second failure, STOP and report incomplete analysis
     - DO NOT proceed with partial data
7. **Validate downloads succeeded:**
   - Check if `database/pr_reviews/{{arg}}/` has artifact directories
   - If empty: STOP and report "No artifacts downloaded - download may have failed silently"
   - Count expected vs actual artifact directories
   - If mismatch: WARN user about missing artifacts

8. Parse test results from all downloaded artifacts:
   - Find all JSON files: `find database/pr_reviews/{{arg}}/ -name "*.json" -type f`
   - For each JSON file:
     ```python
     data = json.load(open(json_file))
     failures = [
         {'test': test_id, 'duration': run['duration'], 'log': run.get('log', ''), 'artifact': artifact_name}
         for test_id, runs in data['tests'].items()
         for run in runs if run['result'] == 'Failed'
     ]
     ```
   - Fall back to HTML if no JSON found:
     - Find HTML files in artifact directories
     - Extract embedded JSON from `data-jsonblob="..."`
     - Parse and extract failures
   - **If no JSON or HTML found:** STOP and report "No test result files found in artifacts"

9. **Categorize failures** by checking error messages:
   - **Transient**: Look for `TRANSIENT FAILURE [Issue #` in error log/message
   - Extract issue number from pattern
   - **New**: All other failures

10. Generate markdown summary with:
   - Run IDs
   - Artifact names and sizes (indicate JSON vs HTML)
   - List artifacts by name
   - **Known transient failures** (✅):
     - Test name
     - Artifact/test type
     - Issue number (with link)
     - Duration
   - **New failures requiring investigation** (❌):
     - Test name
     - Artifact/test type
     - Duration
     - Error preview
   - Total counts

11. **Write summary to file** `database/pr_reviews/{{arg}}/summary`:
   - Write the complete markdown summary
   - This file is used by `/summarize_ci_post` to post to PR
   - Format: Same markdown as displayed to user

**Example output:**
```
Analyzing PR #21218...
Backed up previous review to 21218_backup_20251031_143022
Found 2 failed workflow run(s)

Run 18975780470:
  - Playwright test results JSON (0.1 MB) ⚡
  - Playwright test results JSON (shard 2) (0.1 MB) ⚡

Run 18975780416:
  - Integration test results JSON (0.5 MB) ⚡

================================================================================
FAILURE SUMMARY
================================================================================

✅ Known transient failures (2):
  • test_history_sharing.py::test_sharing_private_history - Issue #12345
    From: Playwright test results JSON
    Duration: 00:01:30
  • test_tool_discovery.py::test_tool_discovery_landing - Issue #67890
    From: Integration test results JSON
    Duration: 00:00:54

❌ New failures requiring investigation (1):
  • test_workflow.py::test_save_workflow
    From: Playwright test results JSON (shard 2)
    Duration: 00:01:15
    Error: AssertionError: Expected element to be visible

Total: 2 transient, 1 new (requires attention)

Summary and artifacts saved to database/pr_reviews/21218/
```

12. **Display and save:**
    - Print summary to user
    - Write same content to `database/pr_reviews/{{arg}}/summary`
    - Create/update symlink: `ln -sfn {{arg}} database/pr_reviews/latest`
    - Notify user: "Summary and artifacts saved to database/pr_reviews/{{arg}}/"

Output concise summary showing categorized failures. Transient failures indicate "safe to re-run", new failures indicate "requires investigation".

**Note:** The summary and downloaded artifacts are saved to `database/pr_reviews/{{arg}}/` for use by `/summarize_ci_post`.

**Marking tests as transient failures:**
To mark a test as a known transient failure, manually add the `@transient_failure(issue=N)` decorator:

```python
from galaxy.util.unittest_utils import transient_failure

@transient_failure(issue=12345)  # GitHub issue number tracking this failure
def test_flaky_feature(self):
    # Test that sometimes fails
    ...
```

Once decorated, future failures will be automatically categorized as transient.
