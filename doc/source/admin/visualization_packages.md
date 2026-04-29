# Visualization Package Administration

Galaxy can manage visualization plugins at runtime through the admin interface instead of requiring a client rebuild.

## Storage model

Runtime-installed visualization packages are stored under `config/visualization_packages/`.

This directory is the managed package store. It is not served directly to users.

Served visualization assets live under `static/plugins/visualizations/`.

This directory is staging output only. Galaxy serves visualizations from here after assets have been staged.

Legacy built-in visualizations under `config/plugins/visualizations/` are still supported and are staged the same way.

## Admin workflow

The visualization admin UI installs npm packages into the managed package store and then stages them into the static serving directory.

Update operations replace the managed package contents first and then re-stage the visualization so Galaxy serves the new version.

Uninstall operations remove both the managed package and any staged assets.

## Startup and recovery

Galaxy stages visualizations on startup so both legacy built-ins and runtime-installed packages are available after a restart.

If staged assets are removed or become stale, use the admin staging controls to re-stage one visualization or all visualizations.

Reloading the visualization registry refreshes plugin discovery, but it does not replace staging.

## Failure behavior

Visualization updates use a safe swap. Galaxy installs the requested version into a temporary location, validates it, and only replaces the current managed package on success.

If the replacement step fails, Galaxy restores the previous managed package and leaves the saved configuration unchanged.
