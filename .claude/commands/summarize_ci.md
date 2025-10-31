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
5. For each failed run, categorize by artifact availability:
   - List artifacts: `gh api repos/galaxyproject/galaxy/actions/runs/<RUN_ID>/artifacts --jq '.artifacts[] | {name: .name, id: .id, size_in_bytes: .size_in_bytes}'`
   - **If run has test artifacts (HTML/JSON):** Mark for download (test failures)
   - **If run has no artifacts:** Mark for log extraction (likely linting, build, or startup failures)
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
7. **Extract logs from runs without artifacts:**
   - For each run marked for log extraction:
   - Get failed job IDs: `gh api repos/galaxyproject/galaxy/actions/runs/<RUN_ID>/jobs --jq '.jobs[] | select(.conclusion == "failure") | {id: .id, name: .name}'`
   - For each failed job, extract relevant error info:
     - Get job logs: `gh api repos/galaxyproject/galaxy/actions/jobs/<JOB_ID>/logs`
     - Parse for common failure patterns:
       - Python linting: Look for "isort", "flake8", "black", "ruff" errors
       - TypeScript: Look for "tsc", "eslint", "prettier" errors
       - Build failures: Look for "error:", "failed", compilation errors
     - Extract last 20-50 lines of relevant errors
     - Save to `database/pr_reviews/{{arg}}/<RUN_ID>_<JOB_NAME>.log`
   - Include job name and extracted errors in summary

8. **Validate downloads succeeded:**
   - Check if `database/pr_reviews/{{arg}}/` has artifact directories OR log files
   - If completely empty: STOP and report "No artifacts or logs extracted - analysis failed"
   - Count expected vs actual artifact directories
   - If mismatch: WARN user about missing artifacts

9. Parse test results from all downloaded artifacts:
   - Find all JSON files: `find database/pr_reviews/{{arg}}/ -name "*.json" -type f`
   - For each JSON file:
     ```python
     data = json.load(open(json_file))
     failures = [
         {'test': test_id, 'duration': run['duration'], 'log': run.get('log', ''), 'artifact': artifact_name, 'result': run['result']}
         for test_id, runs in data['tests'].items()
         for run in runs if run['result'] in ['Failed', 'Error']
     ]
     ```
   - Fall back to HTML if no JSON found:
     - Find HTML files in artifact directories
     - Extract embedded JSON from `data-jsonblob="..."`
     - Parse and extract failures (both 'Failed' and 'Error' results)
   - **If no JSON or HTML found:** STOP and report "No test result files found in artifacts"
   - **Note:** pytest distinguishes 'Failed' (assertion failed) from 'Error' (exception during setup/execution) - both are test failures

10. **Categorize failures** by checking error messages:
   - **Transient**: Look for `TRANSIENT FAILURE [Issue #` in error log/message
   - Extract issue number from pattern
   - **New**: All other failures

11. Generate markdown summary with:
   - Run IDs
   - **For runs with artifacts:**
     - Artifact names and sizes (indicate JSON vs HTML)
     - **Known transient failures** (✅):
       - Test name
       - Artifact/test type
       - Issue number (with link)
       - Duration
     - **New test failures requiring investigation** (❌):
       - Test name
       - Artifact/test type
       - Result type (Failed vs Error)
       - Duration
       - Error preview
   - **For runs without artifacts (linting/build):**
     - Job name (e.g., "Python linting", "client / build-client")
     - Failure type (isort, eslint, build error, etc.)
     - Error count or preview of first few errors
     - Indicate these are NOT test failures
   - Total counts (separate test failures from linting/build failures)

12. **Write summary to file** `database/pr_reviews/{{arg}}/summary`:
   - Write the complete markdown summary
   - This file is used by `/summarize_ci_post` to post to PR
   - Format: Same markdown as displayed to user

**Example output:**
```
Analyzing PR #21218...
Backed up previous review to 21218_backup_20251031_143022
Found 3 failed workflow run(s)

Run 18975780470 (test artifacts):
  - Playwright test results JSON (0.1 MB) ⚡
  - Playwright test results JSON (shard 2) (0.1 MB) ⚡

Run 18975780416 (test artifacts):
  - Integration test results JSON (0.5 MB) ⚡

Run 18975780500 (no artifacts - extracted logs):
  - Python linting

================================================================================
FAILURE SUMMARY
================================================================================

🔧 **Linting/Build failures (1):**
  • Python linting
    Type: isort import ordering
    Files affected: 3
    Example: lib/galaxy/managers/users.py - imports not sorted

✅ **Known transient test failures (2):**
  • test_history_sharing.py::test_sharing_private_history
    From: Playwright test results JSON
    Issue: https://github.com/galaxyproject/galaxy/issues/12345
    Duration: 00:01:30
  • test_tool_discovery.py::test_tool_discovery_landing
    From: Integration test results JSON
    Issue: https://github.com/galaxyproject/galaxy/issues/67890
    Duration: 00:00:54

❌ **New test failures requiring investigation (1):**
  • test_workflow.py::test_save_workflow
    From: Playwright test results JSON (shard 2)
    Type: Failed
    Duration: 00:01:15
    Error: AssertionError: Expected element to be visible

**Total:** 1 linting/build failure, 2 transient tests, 1 new test failure

Summary and artifacts saved to database/pr_reviews/21218/
```

13. **Display and save:**
    - Print summary to user
    - Write same content to `database/pr_reviews/{{arg}}/summary`
    - Create/update symlink: `ln -sfn {{arg}} database/pr_reviews/latest`
    - Notify user: "Summary and artifacts saved to database/pr_reviews/{{arg}}/"

Output concise summary showing categorized failures. Transient failures indicate "safe to re-run", new failures indicate "requires investigation".

**Notes:**
- The summary and downloaded artifacts are saved to `database/pr_reviews/{{arg}}/` for use by `/summarize_ci_post`
- Linting/build failures are extracted from job logs since these jobs don't produce test artifacts
- Common patterns: isort, black, flake8, ruff, eslint, prettier, tsc, build errors
- Log extraction focuses on last 20-50 lines and specific error markers to keep output concise

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
