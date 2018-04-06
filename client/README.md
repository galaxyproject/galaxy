Client Build System
===================

Installs, stages, and builds the client-side scripts necessary for running the
Galaxy webapp. There's no need to use this system unless you are modifying or
developing client-side scripts, or are running the development branch of
Galaxy.

The base dependencies you will need are Node.js and Yarn.  On OSX the easiest
way to get set up is using homebrew and the command `brew install nodejs yarn`.
More information including instructions for other platforms is available  at
nodejs.org and yarnpkg.com.

The Galaxy client build has necessarily grown more complex in the past several
years, but we're still trying to keep things as simple as possible for
developers (everyone, really).  If you're having any trouble with building the
client after following the instructions below please create an issue on GitHub
or reach out for help directly on Gitter at
https://gitter.im/galaxyproject/Lobby.


Complete Client Build
================================================

There are many moving parts to the client build system, but the entrypoint for
most people is the 'client' rule in the Makefile at the root of the Galaxy
repository.  Execute the following to perform a complete build suitable for
local development, including dependency staging, style building, script
processing and bundling.  This is a development-specific build which includes
extra debugging features, and excludes several production optimizations made
during the build process.

    make client

For a production build, suitable for deploying to a live server, use the following:

    make client-production

And, lastly, if you want a production build that includes sourcemaps to allow
for inspection of live javascript to facilitate debugging, use:

    make client-production-maps

Important Note: The development branch of Galaxy does not include client script
artifacts, and these should not be committed.  When issuing a PR to a stable
branch, please run "make client-production-maps", and include those artifacts.
Or, if you'd rather, include only the /client source changes and build
artifacts can be added by maintainers on merge.


Automatic Rebuilding (Watch Mode)
=================================

When you're actively developing, it is sometimes convenient to have the client
automatically rebuild every time you save a file.  You can do this using:

    make client-watch

This will first stage any dependencies (yarn-installed packages like jquery,
etc), and then will watch for changes in any of the galaxy client source files.
When a file is changed, the client will automatically rebuild, after which you
can usually force refresh your browser to see changes.  Note that it is still
recommended to run 'make client' after you are finished actively developing
using 'make client-watch'.


Changing Styles/CSS
===================

The CSS and styling used by Galaxy is also controlled from this directory.
Galaxy uses LESS, a superset of CSS that compiles to CSS, for its styling. LESS
files are kept in client/galaxy/style/less. Compiled CSS is in
static/style/blue.

As mentioned above, 'make client' will also rebuild styles.  If you *only* want
to run the style task, use the following command from the `client` directory:

    yarn run style
