Client Build System
===================

Installs, stages, and builds the client-side scripts necessary for running the
Galaxy webapp. When started through `run.sh` or any other method that utilizes
`scripts/common_startup.sh`, Galaxy will (since 18.09) *automatically* build
the client as a part of server startup, when it detects changes, unless that
functionality is explicitly disabled.

The base dependencies used are Node.js and Yarn.  Galaxy now includes these in
the virtual environment, and they can be accessed by activating that with
`. .venv/bin/activate` from the Galaxy root directory.

If you'd like to install your own dependencies, on OSX the easiest way to get
set up is using `homebrew` and the command `brew install nodejs yarn`.  More
information, including instructions for other platforms, is available at
https://nodejs.org/ and https://yarnpkg.com/ .

The Galaxy client build has necessarily grown more complex in the past several
years, but we are still trying to keep things as simple as possible for
everyone.  If you're having any trouble with building the
client after following the instructions below, please create an issue on GitHub
or reach out for help directly on Gitter at
https://gitter.im/galaxyproject/Lobby .


Complete Client Build
=====================

There are many moving parts to the client build system, but the entry point for
most people is the 'client' rule in the Makefile at the root of the Galaxy
repository.  Execute the following to perform a complete build suitable for
local development, including dependency staging, style building, script
processing, and bundling.  This is a development-specific build which includes
extra debugging features, and excludes several production optimizations made
during the build process.

    make client

For a production build, suitable for deploying to a live server, use the following:

    make client-production

And, lastly, if you want a production build that includes sourcemaps to allow
for inspection of live javascript to facilitate debugging, use:

    make client-production-maps

Important Note: The Galaxy repository does not include client script artifacts,
and these should not be committed.


Automatic Rebuilding (Watch Mode)
=================================

When you're actively developing, it is sometimes convenient to have the client
automatically rebuild every time you save a file.  You can do this using:

    make client-watch

This will first stage any dependencies (yarn-installed packages like jquery,
etc), and then will watch for changes in any of the galaxy client source files.
When a file is changed, the client will automatically rebuild, after which you
can usually force refresh your browser to see changes.  Note that it is still
recommended to run `make client` after you are finished actively developing
using `make client-watch`.


Changing Styles/CSS
===================

Galaxy uses Sass for its styling, which is a superset of CSS that compiles down
to regular CSS.  Most Galaxy styling source (.scss) files are kept in
`client/galaxy/style/scss.  There are additionally style blocks alongside some
Vue components -- styles that are particular to that individual component and
do not apply site-wide.

On build, the compiled css bundle is served at `/static/style/base.css`.

As mentioned above, `make client` will rebuild styles, as a part of the webpack
build.  For iterative development, "Watch Mode" rebuilds as described above do
include style changes.
