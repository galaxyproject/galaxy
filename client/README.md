Client Build System
===================

Installs, stages, and builds the client-side scripts necessary for running the
Galaxy webapp. There's no need to use this system unless you are modifying or
developing client-side scripts.

The base dependencies you will need are Node.js and Yarn.  On OSX the easiest
way to get set up is using homebrew and the command `brew install nodejs yarn`.
More information including instructions for other platforms is available  at
nodejs.org and yarnpkg.com.


Complete Client Build
================================================

There are many moving parts to the client build system, but the entrypoint for
most people is the 'client' rule in the Makefile at the root of the Galaxy
repository.  Execute the following to perform a complete build including
dependency staging, style building, script processing and bundling.

    make client


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


The Toolshed Client Build
=========================

The toolshed client is not tightly integrated with the rest of the build
system.  To build the toolshed client, execute the following command from the
`client` directory.

	yarn run build-toolshed
