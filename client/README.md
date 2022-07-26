# Client Build System

Installs, stages, and builds the client-side scripts necessary for running the
Galaxy webapp. When started through `run.sh` or any other method that utilizes
`scripts/common_startup.sh`, Galaxy will (since 18.09) _automatically_ build
the client as a part of server startup, when it detects changes, unless that
functionality is explicitly disabled.

The base dependencies used are Node.js and Yarn. Galaxy now includes these in
the virtual environment, and they can be accessed by activating that with `.
.venv/bin/activate` from the Galaxy root directory.

If you'd like to install your own dependencies, on OSX the easiest way to get
set up is using `homebrew` and the command `brew install nodejs yarn`. More
information, including instructions for other platforms, is available at
[https://nodejs.org](https://nodejs.org) and
[https://yarnpkg.com/](https://yarnpkg.com).

The Galaxy client build has necessarily grown more complex in the past several
years, but we are still trying to keep things as simple as possible for
everyone. If you're having any trouble with building the client after following
the instructions below, please create an issue on GitHub or reach out for help
directly on Gitter at
[https://gitter.im/galaxyproject/Lobby](https://gitter.im/galaxyproject/Lobby).

## Complete Client Build

There are many moving parts to the client build system, but the entry point for
most people is the 'client' rule in the Makefile at the root of the Galaxy
repository. Execute the following to perform a complete build suitable for
local development, including dependency staging, style building, script
processing, and bundling. This is a development-specific build which includes
extra debugging features, and excludes several production optimizations made
during the build process.

    make client

For a production build, suitable for deploying to a live server, use the
following:

    make client-production

And, lastly, if you want a production build that includes sourcemaps to allow
for inspection of live javascript to facilitate debugging, use:

    make client-production-maps

Important Note: The Galaxy repository does not include client script artifacts,
and these should not be committed.

## Automatic Rebuilding

When you're actively developing, it is convenient to have the client
automatically rebuild every time you save a file. You can do this using:

    make client-watch

This will first stage client dependencies, initiate a build, and then will
watch for changes in any of the galaxy client source files.  When a file is
changed, the client will automatically rebuild, after which you can refresh
your browser to see changes.

For even more rapid development you can use the webpack development server,
which takes advantage of hot module replacement (HMR). This technique allows
swapping out of javascript modules while the application is running without
requiring a full page reload most of the time, at least in the more modern
parts of the application.

The command below starts a special webpack dev server after a client
build.

    make client-dev-server

This will start up an extra client development server running on port 8081.
Open your browser to http://localhost:8081 (instead of the default 8080 that
Galaxy would run on), and you should see Galaxy like normal.  Except now, when
you change client code it'll automatically rebuild *and* reload the relevant
portion of the application for you. Lastly, if you
are running Galaxy at a location other than the default, you can specify a
different proxy target (in this example, port 8000) using the GALAXY_URL
environment variable:

    GALAXY_URL="http://localhost:8000" make client-dev-server

Sometimes you want to run your local UI against a remote Galaxy server. This is also possible, if you enable `CHANGE_ORIGIN` flag 

    CHANGE_ORIGIN=true GALAXY_URL="https://usegalaxy.org/" make client-dev-server

## Changing Styles/CSS

Galaxy uses Sass for its styling, which is a superset of CSS that compiles down
to regular CSS. Most Galaxy styling source (.scss) files are kept in
`client/src/style/scss`. There are additionally style blocks alongside some Vue
components -- styles that are particular to that individual component and do
not apply site-wide.

On build, the compiled css bundle is served at `/static/style/base.css`.

As mentioned above, `make client` will rebuild styles, as a part of the webpack
build. For iterative development, "Watch Mode" rebuilds as described above do
include style changes.

## Client-Side Unit Testing

Galaxy's client is undergoing an extensive refactoring and modernizing process.
As part of this initiative, we would like to request that all new client-side
code submissions come with accompanying javascript unit-tests for the
developer-facing API of your new code.

### Testing Technologies

[Galaxy uses Jest](https://jestjs.io/) for its client-side unit testing
framework.

For testing Vue components, we use the [Vue testing
utils](https://vue-test-utils.vuejs.org/) to mount individual components in a
test bed and check them for rendered features.  Please use jest-based mocking
for isolating test functionality.

A set of older qUnit tests also exist which will be phased-out as the code they
support is replaced with modern component-based implementations. In the
meantime, we still run the qunit tests in sequence.

### Running the tests

#### At Build-Time

To simply run all the javascript unit tests, you can use make from the root
directory. This is what happens during a complete client build.

     make client-test

#### During Development

During client-side development, it is more convenient to have granular testing
options. The various testing scripts are defined inside package.json within the
client folder, and are called with `yarn` as demonstrated in the
following commands.

This is what CI is going to run, and also what 'make client-test' invokes,
executing all the client tests:

     yarn run test

You can also bypass qunit and single-run all of the jest tests like so:

     yarn run jest

Or, if you really want to run just the qunit tests:

    yarn run qunit

##### Watch and rerun jest unit tests every time a source file changes

This is incredibly handy, and there are a host of options in the interactive
terminal this starts for executing Jest tests.

     yarn run jest-watch

##### Run only specified test files when a source file changes

    yarn run jest-watch MyModule

    yarn run jest-watch Dialog

    yarn run jest-watch workflow/run
