Client Build System
===================

Builds and moves the client-side scripts necessary for running the Galaxy webapps. There's no need to use this system
unless you are modifying or developing client-side scripts.

You'll need Node and the Node Package Manager (npm): nodejs.org.

Once npm is installed, install the grunt task manager and it's command line into your global scope:

    npm install -g grunt grunt-cli

Next, from within this directory, install the local build dependencies:

    cd client
    npm install

You're now ready to re-build the client scripts after modifying them.


Rebuilding
==========

There are two methods for rebuilding: a complete rebuild and automatic, partial rebuilds while you develop.

A complete rebuild can be done with the following (from the `client` directory):

    grunt

This will:

1. compress the files in client/galaxy/scripts and place them in static/scripts
2. generate source maps and place them in static/maps


Templates
=========

You can change and recompile the templates by using:

    grunt templates

This will:

1. recompile the templates in client/galaxy/scripts/templates to client/galaxy/scripts/templates/compiled
2. minify and generate source maps for the compiled templates


Changing Styles/CSS
===================

The CSS and styling used by Galaxy is also controlled from this directory. Galaxy uses LESS, a superset of CSS that
compiles to CSS, for its styling. LESS files are kept in client/galaxy/style/less. Compiled CSS is in statis/style/blue.

Use grunt to recompile the LESS in into CSS (from the `client` directory):

    grunt style


Grunt watch
===========

Grunt can also do an automatic, partial rebuild of any files you change *as you develop* by:

1. opening a new terminal session
2. `cd client`
3. `grunt watch`

This starts a new grunt watch process that will monitor the files in `client/galaxy/scripts` for changes and copy and
pack them when they change.

You can stop the `grunt watch` task by pressing `Ctrl+C`. Note: you should also be able to background that task if you
prefer.


Using a Locally Installed Version of Grunt
==========================================

A non-global version of grunt and the grunt-cli are installed when using 'npm install'. If you'd rather build with that
version, you'll need to use the full, local path when calling it:

    ./node_modules/.bin/grunt
    # or
    ./node_modules/.bin/grunt watch


The Toolshed Client Build
=========================

The commands mentioned above in 'Rebuilding' and 'Grunt watch' also can be applied to toolshed scripts by using the
`--app=toolshed` option:

	grunt watch --app=toolshed
	grunt --app=toolshed