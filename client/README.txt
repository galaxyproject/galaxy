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

This will copy any files in `client/galaxy/scripts` to `static/scripts` and run `static/scripts/pack_scripts.py` on all.

Grunt can also do an automatic, partial rebuild of any files you change *as you develop* by:

    1. opening a new terminal session
    2. `cd client`
    3. `grunt watch`

This starts a new grunt watch process that will monitor the files in `client/galaxy/scripts` for changes and copy and
pack them when they change.

You can stop the `grunt watch` task by pressing `Ctrl+C`. Note: you should also be able to background that task if you
prefer.
