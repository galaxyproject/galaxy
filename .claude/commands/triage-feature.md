Persona: You are a senior engineer responsible for maintaining the Galaxy project.

Arguments:
- $ARGUMENTS - Github issue number and optional work level (low/medium/high, default: medium)
  Examples: "21474", "21474 low", "21474 high"

Parse the issue number and work level from $ARGUMENTS. Work levels control triage depth:
- **low**: Research and understand only, skip implementation planning
- **medium**: Research + single recommended approach with focused plan
- **high**: Research + multiple approaches + comprehensive plan

You will be supplied a Github issue number for a feature request to triage. A Galaxy developer will be assigned the issue but your job is to structure the conversation around the feature.

Fetch the issue using "gh issue view <number>" and write the issue contents to ``FEATURE_<#>.md``.

In serial launch subagents to perform actions to help in the triage process. As the agent responsible for the triage process - please read the artifacts generated from subagents and direct the process as it makes sense. Your job is direct the process though - do not try to implement the feature or do research yourself.

When to launch subagents and what they should do are as follows:

- When: Always (all levels)
  What: Launch a subagent to research user demand signals. This subagent should create a document called ``FEATURE_<#>_DEMAND.md``. The subagent should analyze: issue reactions/thumbs up, linked/duplicate issues, comment frequency and sentiment, any related discussion threads. Quantify demand where possible.
- When: Always (all levels)
  What: Launch a subagent to research the codebase for related functionality. This subagent should create a document called ``FEATURE_<#>_CODE_RESEARCH.md``. The subagent should find: existing similar features, relevant extension points, architectural patterns to follow, and files/modules that would need modification.
- When: Work level is **high** and the feature has multiple possible implementation approaches
  What: Launch a subagent to develop alternative implementation approaches. Create a document called ``FEATURE_<#>_APPROACHES.md``. This document should outline 2-4 approaches with tradeoffs (complexity, breaking changes, performance, maintainability).
- When: Always (all levels)
  What: Launch a subagent to assess importance. Create a document called ``FEATURE_<#>_IMPORTANCE.md``. Assess:
  - User demand (high/medium/low) based on reactions, comments, linked issues
  - Strategic value (high/medium/low) - does it align with project direction, enable other features, improve UX significantly
  - Effort estimate (small/medium/large/xlarge) based on code research
  - Risk assessment (breaking changes, migration needs, security considerations)
  - Recommendation: prioritize now / backlog / defer / decline with rationale
- When: Work level is **medium** - create a focused implementation plan
  What: Launch a subagent to read the research documents and create an implementation plan for the single recommended approach. Create a document called ``FEATURE_<#>_PLAN.md``. Include: recommended approach, affected files, testing strategy, migration considerations if any.
- When: Work level is **high** - create a comprehensive implementation plan
  What: Launch a subagent to read all research documents (including approaches) and create a detailed implementation plan. Create a document called ``FEATURE_<#>_PLAN.md``. Include: recommended approach with rationale for choosing it over alternatives, affected files, testing strategy, migration considerations if any.

Once all of the subagents are done - please write a new document called ``FEATURE_<#>_SUMMARY.md``.

This document should contain:
- A concise one paragraph top-line summary about the feature request and recommended approach.
- Importance assessment summary: demand level, strategic value, effort, and overall priority recommendation.
- Key questions for the group discussion that would help refine requirements or approach.
- Any concerns about scope creep, breaking changes, or long-term maintenance burden.

Publish all the relevant documents to a gist and print a comment to the user that they can post to the Github issue to aid with the triage process.
