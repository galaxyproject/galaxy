# Visualization Package Administration

Galaxy can manage visualization plugins at runtime through the admin interface instead of requiring a client rebuild.

## Storage model

Runtime-installed visualization packages are stored in the directory set by `visualization_packages_dir`, and the list of installed packages is recorded in `visualization_packages_config_file`. Both are relative to `managed_config_dir`, so when running Galaxy from source they default to `config/visualization_packages/` and `config/visualization_packages.yml`.

This directory is the managed package store. It is not served directly to users.

Served visualization assets live under `static/plugins/visualizations/`.

This directory is staging output only. Galaxy serves visualizations from here after assets have been staged.

Legacy built-in visualizations under `config/plugins/visualizations/` are still supported and are staged the same way.

## Package requirements

A package is a Galaxy visualization if it ships `static/<id>.xml`, where `<id>` is the visualization ID it's installed under (for example, `@galaxyproject/h5web` ships `static/h5web.xml`). That XML is what the visualization registry loads, and the client build makes the same check for the visualizations listed in `client/visualizations.yml`.

Install and update refuse any package version without it. A failed install leaves nothing behind, and a failed update keeps the current version in place.

Some older releases under `@galaxyproject` predate this layout and can't be installed: `msa`, `bamjs`, `charts` (a utility library) and `pv_load`. None of them are in the galaxy-visualizations repository anymore.

## Finding packages

The Available tab lists every package published under the `@galaxyproject` npm scope. That includes packages that aren't visualizations at all (`galaxy-client`, `gx-it-proxy`, `brand-tokens` and so on). Installing one of those fails with a message explaining that it doesn't include a visualization XML.

npm keywords can't be used to narrow the list today: almost none of the published visualization packages carry a `visualization` keyword, and the few that do include the outdated releases above. The plan is for the galaxy-visualizations release process to tag every package with a `galaxy-visualization` keyword, after which this list can filter on it.

## Admin workflow

The visualization admin UI installs npm packages into the managed package store and then stages them into the static serving directory.

Update operations replace the managed package contents first and then re-stage the visualization so Galaxy serves the new version.

Uninstall operations remove the managed package and its staged assets. If Galaxy has a built-in visualization with the same ID, the built-in is staged again in its place.

Disabling a package keeps it installed but stops serving it: its staged assets are removed, or replaced by the built-in of the same ID if there is one. Enabling it stages it again.

Each of these changes reloads the visualization registry in every Galaxy process, so the result is visible right away.

## Startup and recovery

Galaxy stages visualizations on startup so both legacy built-ins and runtime-installed packages are available after a restart.

If staged assets are removed or become stale, use the admin staging controls to re-stage one visualization or all visualizations.

Reloading the visualization registry refreshes plugin discovery, but it does not replace staging. Admin actions reload it automatically; the manual reload is only needed after changing files on disk outside the admin UI.

## Failure behavior

Visualization updates use a safe swap. Galaxy installs the requested version into a temporary location, validates it, and only replaces the current managed package on success.

If the replacement step fails, Galaxy restores the previous managed package and leaves the saved configuration unchanged.
