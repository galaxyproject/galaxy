Persona: You are the lead engineer running the weekly Galaxy triage meeting.

Arguments:

- $ARGUMENTS - Optional: `[project_number] [column_name] [work_level]`
  Defaults: project 26, column "Triage/Discuss", work level "medium"
  Examples: "" (all defaults), "26", "26 Triage/Discuss low", "26 Triage/Discuss high"

Parse arguments from $ARGUMENTS. If fewer than 3 are provided, use defaults for the missing ones. Work levels: low (research only), medium (research + single plan), high (research + all theories + assessment).

## Step 1: Fetch project board issues

Run `gh project item-list <project_number> --owner galaxyproject --format json --limit 500` to get all items.

Filter the JSON results to only items where `status` matches the target column name. Extract issue numbers and titles. Print the count of issues found in the column.

## Step 2: Filter to uncommented issues

For each issue, run `gh issue view <number> --repo galaxyproject/galaxy --json comments,assignees` to check the comment count and assignees. Skip an issue if:

- It has 1+ comments (already being discussed)
- It has any assignees (already claimed by someone)

Print how many issues need triage out of the total, noting how many were skipped for each reason. If zero issues remain, print a summary and stop.

## Step 3: Launch triage agents in parallel batches

Process uncommented issues in batches of up to 5 parallel Task agents. Each agent receives:

- The issue number and work level
- Instructions to read `.claude/commands/triage-issue.md` and follow its full workflow (which classifies the issue and dispatches to triage-bug.md or triage-feature.md)
- The triage-issue skill already handles: classification, launching research/planning subagents, writing artifact files, creating a gist, and drafting a comment

**Important override for batch mode:** Tell each agent to NOT ask the user for classification confirmation if ambiguous — default to bug. Also tell each agent to post the triage comment directly to the issue using `gh issue comment NUM --repo galaxyproject/galaxy` instead of printing it for the user to copy. The comment should include the gist link.

## Step 4: Collect results and print summary

As each agent completes, collect its findings. Print a final markdown summary table:

| Issue | Title | Type | Recommendation | Complexity | Gist |
| ----- | ----- | ---- | -------------- | ---------- | ---- |

Include a row for each triaged issue. For skipped issues (already had comments or assignees), note them below the table.

Print total counts: issues in column, skipped (had comments), skipped (assigned), triaged, failed.
