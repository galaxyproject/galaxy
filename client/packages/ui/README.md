# @galaxyproject/galaxy-ui

Galaxy's G-prefixed base components (GButton, GTable, GModal, ...) and the composables and tokens
they need. It ships raw source, not a build: each consumer compiles the SFCs with its own Vue.

## Consumers

- **The Galaxy client** imports it as a `workspace:*` dependency, aliased to `src/index.ts` in
  `client/vite.config.mjs`. It runs on Vue 3 under `@vue/compat`, with Bootstrap 4 on the page.
- **The Tool Shed frontend** (`lib/tool_shed/webapp/frontend`) installs it as
  `file:../../../../client/packages/ui`. It runs on plain Vue 3, with no `@vue/compat` and no
  Bootstrap, and imports `@galaxyproject/galaxy-ui/tokens.css` for the design tokens.

So a change has to work in both. In particular:

- Vue 2-only syntax (`.native`, `value`/`input` v-model, a bare `<template>` without a directive)
  can look fine under compat and break in the shed. `src/portableImports.test.ts` guards some of this.
- Bootstrap styles the client's markup for free. Anything a component needs to look right has to be
  in its own styles; baselines that only restate Bootstrap go in `:where()` so they stay at zero
  specificity and the client keeps Bootstrap's look.
- Read colours, spacing and fonts from the tokens in `src/styles/tokens.css` (`var(--color-blue-600)`
  and so on) rather than literal values, so both consumers can theme them.

## Changing dependencies

The shed's `file:` install resolves this package's `dependencies` and `peerDependencies` into
`lib/tool_shed/webapp/frontend/pnpm-lock.yaml`. After changing either, run `pnpm install` in
`lib/tool_shed/webapp/frontend` and commit its lockfile too; otherwise the shed's
`--frozen-lockfile` install fails in CI.

pnpm installs `file:` dependencies as hard links, so while developing the shed against local edits
here, an editor that saves by replacing the file, or a newly added file, isn't picked up until
`pnpm install --force` in the shed (and a Vite restart with `--force`).
