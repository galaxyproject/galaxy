# client/packages/

Workspace packages consumed by the main client as `workspace:*` deps. The main client (`client/package.json`, `client/src/`) is the workspace root.

| Package                        | Published                                | Purpose                                                    |
| ------------------------------ | ---------------------------------------- | ---------------------------------------------------------- |
| [`api-client/`](./api-client/) | Yes (`@galaxyproject/galaxy-api-client`) | OpenAPI schema types, typed fetch client, error utilities. |

## Criteria for adding a package

A package boundary has real cost. Adding one needs:

- Zero Galaxy-specific coupling (no stores, session, routing, auth).
- No existing npm substitute (don't republish `@vueuse/core` or `lodash` equivalents).
- Either a real external consumer or a real internal architectural case -- a migration target, an enforced dependency-direction boundary. See the decomposition issue ([#13336](https://github.com/galaxyproject/galaxy/issues/13336)) before extracting.

## How it works

- `client/pnpm-workspace.yaml` declares `packages/*` as members; single `client/pnpm-lock.yaml`.
- A `postinstall` on `client/package.json` builds each workspace package so `dist/` is present for `vue-tsc` and production `vite build`.
- `client/vite.config.mjs` has a conditional `resolve.alias` that maps `@galaxyproject/*` imports directly to package source during `vite serve` -- edits HMR without a rebuild. Production builds use `dist/`.

## Published vs internal

Published packages have a Galaxy-release-tied version and ship via `publish_artifacts.yaml`. Internal packages (`"private": true`) exist for the architectural boundary only; flip to published by removing `"private": true` and adding a publish step.

## Common ops (from `client/`)

```bash
pnpm install                                                  # workspace + postinstall builds
pnpm --filter @galaxyproject/galaxy-api-client test           # scoped command
pnpm --filter @galaxyproject/galaxy-api-client run build
make update-client-api-schema                                 # from galaxy root
```
