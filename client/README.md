Client Build System
===================

Builds and moves the client-side scripts necessary for running the Galaxy
webapps. There's no need to use this system unless you are modifying or
developing client-side scripts.

The base dependencies you'll need are Node.js and the Node Package Manager
(npm).  See nodejs.org for more information.


Simple Full Build
=================

The simplest way to rebuild the entire client to incorporate any local changes
is to run the 'client' rule in the Galaxy makefile, which is in the repository
root.  This will also ensure any local node modules are installed.

    make client


Detailed Build Instructions
===========================

Once npm is installed, use it to install the local build dependencies in the
`client` directory:

    cd client
    npm install

You're now ready to re-build the client scripts after modifying them.


Rebuilding
==========

There are two methods for rebuilding: a complete rebuild and automatic,
partial rebuilds while you develop.

A complete rebuild can be done with the following (from the `client`
directory):

    npm run all

This will:

1. compress the files in client/galaxy/scripts and place them in static/scripts
2. generate source maps and place them in static/maps
3. rebuild the webpack-based client apps


Rebuilding Scripts Only
=======================

To re-minify all the individual javascript files:

    npm run scripts


Rebuilding Webpack Apps
=======================

To rebuild the webpack bundles for apps (compressed for production):

    npm run webpack

To rebuild the apps without compression:

    npm run webpack-dev

To rebuild without compression and watch and rebuild when scripts change:

    npm run webpack-watch


Changing Styles/CSS
===================

The CSS and styling used by Galaxy is also controlled from this directory. Galaxy uses LESS, a superset of CSS that
compiles to CSS, for its styling. LESS files are kept in client/galaxy/style/less. Compiled CSS is in static/style/blue.

Use grunt to recompile the LESS in into CSS (from the `client` directory):

    npm run style


Grunt watch
===========

Grunt can also do an automatic, partial rebuild of any files you change *as you develop* by:

1. opening a new terminal session
2. `cd client`
3. Watch with:
    1. `npm run watch` to watch the *scripts/* folder
    2. `npm run watch-style` to watch the *style/* folder

This starts a new grunt watch process that will monitor the files, in the corresponding folder, for changes and copy and
rebuild them when they change.

You can stop the watch task by pressing `Ctrl+C`. Note: you should also be able to background that task
if you prefer.


The Toolshed Client Build
=========================

The commands mentioned above in 'Rebuilding' and 'Grunt watch' also can be applied to toolshed scripts by using the
`--app=toolshed` option:

	npm run grunt watch --app=toolshed
	npm run grunt --app=toolshed
