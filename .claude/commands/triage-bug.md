Persona: You are a senior engineer responsible for maintaining the Galaxy project.

Arguments:
- $ARGUMENTS - Github issue number and optional work level (low/medium/high, default: medium)
  Examples: "21536", "21536 low", "21536 high"

Parse the issue number and work level from $ARGUMENTS. Work levels control triage depth:
- **low**: Research and understand only, skip fix planning
- **medium**: Research + single plan for most probable cause
- **high**: Research + plans for all theories + plan assessment

You will be supplied a Github issue number to triage. A Galaxy developer will be assigned the issue but your job is to structure the conversation around the issue.

Fetch the issue using "gh issue view <number>" and write the issue contents to ``ISSUE_<#>.md``.

Galaxy versions look like 24.1, 26.2, etc.. and these correspond to branches such as release_24.1, release_26.2, etc.. Be sure you're on the target branch before continuing.

In serial launch subagents to perform actions to help in the triage process. As the agent responsible for the triage process - please read the artifacts generated from subagents and direct the process as it makes sense. Your job is direct the process though - do not try to fix the issue or do research yourself.

When to launch subagents and what they should do are as follows:

- When: Always (all levels)
  What: Launch a subagent to research the issue. This subagent should create a document called ``ISSUE_<#>_CODE_RESEARCH.md`` where ``<#>`` is the issue number. The subagent should attempt to find the source issue, summarize the code relevant issue, file paths, and develop (roughly 1-3) theories about the possible true cause of the issue.
- When: The issue is complex and if the issue seems like a regression (all levels)
  What: Launch a subagent to read in the "code research" document and develop theories about when the issue was introduced. Create a document called ``ISSUE_<#>_HISTORY.md`` where ``<#>`` is the issue number. This document should include links to pull requests that are relevant, authors that have touched the code, etc...
- When: Work level is **medium** - create ONE plan for the most probable cause
  What: Launch a subagent to come up with a detailed plan to fix the issue with the most probable root cause identified in the code research. Create a document called ``ISSUE_<#>_PLAN.md``.
- When: Work level is **high** - create a plan for EACH cause identified
  What: Launch a subagent for each true cause identified to come up with a detailed plan to fix the issue with the assumed root cause. Create a document called ``ISSUE_<#>_PLAN_<cause>.md`` where cause is a short description of the cause of issue distinguishing it from the other root causes.
- When: Work level is **high** only
  What: Launch a subagent to read the code research and the relevant plans to address the issue. This subagent should evaluate the quality of the plans and assess the probability of each to solve the problem. This subagent should create a document called ``ISSUE_<#>_PLAN_ASSESSMENT.md``.
- When: Always (all levels)
  What: Launch a subagent to assess bug importance. Create a document called ``ISSUE_<#>_IMPORTANCE.md``. Assess:
  - Severity (critical/high/medium/low): data loss/security > crash/hang > functional breakage > cosmetic/minor
  - Blast radius: all users, specific configurations, edge cases only
  - Workaround existence: none / painful / acceptable
  - Regression status: new regression (which version) vs long-standing
  - User impact signals: issue reactions, duplicate reports, support requests
  - Recommendation: hotfix / next release / backlog / wontfix with rationale

Once all of the subagents are done - please write a new document called ``ISSUE_<#>_SUMMARY.md``.

This document should contain:
- A concise one paragraph top-line summary about the issue that we will use to guide the discussion about the issue. Including the most probable fix and most probable true cause (with source of the regression if you've collected an issue history document).
- Importance assessment summary: severity, blast radius, regression status, and overall priority recommendation.
- Any relevant questions about the context around the issue that would be helpful in debugging and guiding the discussion as a large group.
- An estimate on the effort required to fix the issue, an assessment on how difficult it is to recreate and test the issue.

Publish all the relevant documents to a gist and print a comment to the user that they can post to the Github issue to aid with the triage process and offer to copy that comment to the clipboard. The comment should be concise but should include all relevant data and questions from the summary document.
