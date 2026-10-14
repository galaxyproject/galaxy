# Reviewing Galaxy stories

Run `pnpm storybook` from `client/` to browse component states. Use the viewport
menu to check desktop, a 400px Galaxy panel, and mobile layouts. Measure/outline
tools help inspect spacing. These tools aid review; viewport presets do not
multiply automated tests or capture screenshot baselines.

## Accessibility

`@storybook/addon-a11y` runs axe after stories render and their plays finish.
The Accessibility panel shows violations, passes, and incomplete checks, with
highlighting and links to explanations. Its toolbar also simulates vision
impairments. Enable **Accessibility** in the expanded test widget when running
component tests inside Storybook.

`pnpm test:browser` runs the same checks in Chromium. The preview sets
`a11y.test: "error"`, so violations fail the command. The rulesets retain WCAG
2.0/2.1 A and AA plus best practices, and add WCAG 2.2 AA (including target size).
Axe's context is `body` so teleported dialogs and menus are included. Storybook
keeps the `region` rule disabled for isolated components; full-page stories may
explicitly enable it. AAA rules are not enabled globally.

Legacy violations are marked with `parameters: { a11y: { test: "todo" } }`
in the affected story, with a comment naming the observed rule. The initial
[story-by-story audit](A11Y_AUDIT.md) records the exceptions. Remove each
exception after fixing the component and rerunning its stories. `todo` still
runs axe and shows warnings in Storybook, but **does not report violations or
fail the CLI/CI run**. Avoid `off`, `manual: true`, broad DOM exclusions, and
blanket rule disables to hide defects.

Checks run on the final rendered state. Plays must wait for asynchronous content
and leave the state being audited visible. Use separate stories for an open
modal, expanded menu, and validation errors that a longer play later dismisses.
Automated checks cover only some accessibility issues; keep keyboard/focus/name
assertions in plays and manually review important screen-reader interactions.

## Visual regression testing

This branch provides states and review tools, not automated pixel comparisons.
Storybook's documented visual-test addon uses Chromatic and needs a linked
account/project. It captures after the play finishes, not after every step.
Vitest Browser Mode also supports `toMatchScreenshot` with the existing
Playwright provider if we choose to own baselines and diff artifacts locally.
Pick a consistent capture environment and viewport before adopting either.

- [Accessibility configuration](https://storybook.js.org/docs/writing-tests/accessibility-testing)
- [Visual testing](https://storybook.js.org/docs/writing-tests/visual-testing)
- [Chromatic play snapshots](https://www.chromatic.com/docs/interactions/)
- [Vitest screenshot comparisons](https://main.vitest.dev/guide/browser/visual-regression-testing)
