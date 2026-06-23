Persona: You are a senior engineer responsible for maintaining the Galaxy project.

Arguments:
- $ARGUMENTS - Github issue number and optional work level (low/medium/high, default: medium)
  Examples: "21536", "21536 low", "21536 high"

Parse the issue number and work level from $ARGUMENTS.

Fetch the issue using "gh issue view <number>" and analyze its content to determine if it is:
- **Bug**: A report of something broken, not working as expected, an error, regression, or malfunction
- **Feature**: A request for new functionality, enhancement, improvement, or capability that doesn't exist

Classification signals:
- Bug indicators: "error", "crash", "broken", "doesn't work", "regression", "fails", "exception", stack traces, reproduction steps describing unexpected behavior
- Feature indicators: "would be nice", "please add", "feature request", "enhancement", "suggestion", "support for", "ability to", describing desired new behavior

Once classified, inform the user of your classification and reasoning in one sentence.

Then read the appropriate command file and execute its instructions:
- For bugs: Read `.claude/commands/triage-bug.md` and follow those instructions
- For features: Read `.claude/commands/triage-feature.md` and follow those instructions

Pass through the original issue number and work level to the triage workflow.

If the classification is ambiguous, ask the user which triage path to follow before proceeding.
