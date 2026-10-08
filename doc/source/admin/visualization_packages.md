# Visualization Package Administration

Galaxy can manage visualization plugins at runtime through the admin interface instead of requiring a client rebuild.

## Storage model

Runtime-installed visualization packages are stored in the directory set by `visualization_packages_dir`, and the list of installed packages is recorded in `visualization_packages_config_file`. Both are relative to `managed_config_dir`, so when running Galaxy from source they default to `config/visualization_packages/` and `config/visualization_packages.yml`.

This is the managed package store. Galaxy loads installed packages straight from it and serves their files through `/api/plugins/<name>/static/...`; nothing is copied into Galaxy's own `static/` directory. If several Galaxy servers share a database, they should share this directory too (and the config file next to it), so they all see the same packages.

The visualizations Galaxy ships with are unchanged: the client build installs the ones listed in `client/visualizations.yml` into `static/plugins/visualizations/`, and they're served from `/static/plugins/visualizations/<name>/static/...` as before, by Galaxy or by your web server.

An installed package with the same ID as a built-in visualization replaces it while the package is enabled.

## Read-only Galaxy installs (CVMFS)

Because runtime packages never touch `static/`, this works when the Galaxy tree is read-only, for example served from CVMFS with `static_enabled: false` and `/static` served by nginx. Only `managed_config_dir` (or wherever `visualization_packages_dir` and `visualization_packages_config_file` point) needs to be writable.

No web server changes are needed: package files are served under `/api/`, which is already proxied to Galaxy. If you've set up `nginx_x_accel_redirect_base`, Galaxy hands the file transfer off to nginx the same way it does for dataset downloads.

## Package requirements

A package is a Galaxy visualization if it ships `static/<id>.xml`, where `<id>` is the visualization ID it's installed under (for example, `@galaxyproject/h5web` ships `static/h5web.xml`). That XML is what the visualization registry loads, and the client build makes the same check for the visualizations listed in `client/visualizations.yml`.

Install and update refuse any package version without it. A failed install leaves nothing behind, and a failed update keeps the current version in place.

Some older releases under `@galaxyproject` predate this layout and can't be installed: `msa`, `bamjs`, `charts` (a utility library) and `pv_load`. None of them are in the galaxy-visualizations repository anymore.

## Finding packages

The Available tab lists every package published under the `@galaxyproject` npm scope. That includes packages that aren't visualizations at all (`galaxy-client`, `gx-it-proxy`, `brand-tokens` and so on). Installing one of those fails with a message explaining that it doesn't include a visualization XML.

npm keywords can't be used to narrow the list today: almost none of the published visualization packages carry a `visualization` keyword, and the few that do include the outdated releases above. The plan is for the galaxy-visualizations release process to tag every package with a `galaxy-visualization` keyword, after which this list can filter on it.

## Admin workflow

The visualization admin UI installs npm packages into the managed package store. Update replaces a package's contents with the new version, and uninstall removes it; if Galaxy ships a visualization with the same ID, that one comes back into use.

Disabling a package keeps it installed but stops loading it, so the built-in of the same ID (if any) is used instead. Enabling it switches back.

Each of these changes reloads the visualization registry in every Galaxy process, so the result is visible right away. The Refresh button reloads it by hand, which is only needed after changing the package store outside the admin UI.

## Failure behavior

Visualization updates use a safe swap. Galaxy installs the requested version into a temporary location, validates it, and only replaces the current managed package on success.

If the replacement step fails, Galaxy restores the previous managed package and leaves the saved configuration unchanged.
