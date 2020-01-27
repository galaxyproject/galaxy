Client Build System
===================

Installs, stages, and builds the client-side scripts necessary for running the
Galaxy webapp. When started through `run.sh` or any other method that utilizes
`scripts/common_startup.sh`, Galaxy will (since 18.09) *automatically* build
the client as a part of server startup, when it detects changes, unless that
functionality is explicitly disabled.

The base dependencies used are Node.js and Yarn.  Galaxy now includes these in
the virtual environment, and they can be accessed by activating that with `.
.venv/bin/activate` from the Galaxy root directory.

If you'd like to install your own dependencies, on OSX the easiest way to get
set up is using `homebrew` and the command `brew install nodejs yarn`.  More
information, including instructions for other platforms, is available at
https://nodejs.org/ and https://yarnpkg.com/ .

The Galaxy client build has necessarily grown more complex in the past several
years, but we are still trying to keep things as simple as possible for
everyone.  If you're having any trouble with building the client after
following the instructions below, please create an issue on GitHub or reach out
for help directly on Gitter at https://gitter.im/galaxyproject/Lobby .


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

For a production build, suitable for deploying to a live server, use the
following:

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

Note that there's a new, better option described in the next section.  This
method of building will likely be deprecated as HMR is more widely tested.


Even Better Automatic Rebuilding (HMR)
======================================

For even more rapid development you can use the webpack development server for
Hot Module Replacement (HMR).  This technique allows swapping out of modules
while the application is running without requiring a full page reload most of
the time.

Setting this up is a little more involved, but it is the fastest possible way
to iterate when developing the client.  You'll need to start two separate
processes here.  The first command below starts a special webpack dev server
after a client build, and the second starts a Galaxy server like usual, but
with extra mappings that redirect client artifact requests to the mentioned
webpack dev server.

    make client-dev-server
    GALAXY_CLIENT_DEV_SERVER=1 sh run.sh

Note that this only works under uWSGI due to the extra internal routing rules
employed.  If you're using the older Paste-based galaxy webserver you'll need
to swap it over to take advantage of this functionality.


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


# Client-Side Unit Testing

Galaxy's client is undergoing an extensive refactoring and modernizing process.
As part of this initiative, we would like to request that all new client-side
code submissions come with accompanying javascript unit-tests for the
developer-facing API of your new code.

## Testing Technologies

[Galaxy uses Mocha](https://mochajs.org/) for its client-side unit testing
framework with [Chai as its assertion library](https://www.chaijs.com/) and
[karma as a test runner](https://karma-runner.github.io/latest/index.html).
The karma configs are contained in the client/karma folder. Unit tests are run
using Chrome headless by default.

For testing Vue components, we use the [Vue testing
utils](https://vue-test-utils.vuejs.org/) to mount individual components in a
test bed and check them for rendered features.

We use the [babel plugin
Rewire](https://github.com/speedskater/babel-plugin-rewire) to mock imported
ES6 dependencies during unit-testing. [Sinon](https://sinonjs.org/) is also
available for more robust stubbing, mocking and spying utilities.

A set of older qUnit tests also exist which will likely be phased-out as the
code they support is replaced with modern component-based implementations. In
the meantime, karma runs both the mocha and qunit tests in sequence.


## Running the tests

### At Build-Time
To simply run all the javascript unit tests, you can use make from the root
directory. This is what happens during a complete client build.

     make client-test


### During Development

During client-side development, it is more convenient to have granular testing
options. The various testing scripts are defined inside package.json within the
client folder, and are called either with `yarn` as demonstrated in the 
following commands.

#### Run all tests (mocha and qunit):

     yarn run test

#### Watch and rerun all client-side unit-tests every time a source file changes:

     yarn run test-watch

#### Run only specified test files when a source file changes:

    yarn run test-watch watch-only="Tags/*.test.js"

(The above watch-only parameter will be mapped to the following glob expression "**/Tags/*.test.js")

#### Run qunit legacy tests

    yarn run test-qunit


## Writing a test file

The karma configs are setup to look at any file ending in "*.test.js". Please
place your test files inside client/galaxy/scripts folders right next to
whatever files that they are testing.

```javascript
// yourtestfile.test.js

import { things } from "./yourtestfile.js";

describe("some module you wrote", () => {

    let transientVariables, serviceInstances, testData;

    beforeEach(() => {
        // setup your code (if necessary)
    })

    afterEach(() => {
        // teardown your code (so it doesn't ruin the next test)
    })

    it("should do something or other", () => {
        assert(somethingThatShouldTrue, "explain what went wrong");
        expect(something).to.eq(true);
    })
})
```


## Testing ~~Suggestions~~ Obligations


### Clearly document the intent of your test

Please remember that these tests are not *for* you. They're for the people who
come after you. It will be a lot easier to modify, repair and upgrade your code
if they can figure out what you were originally hoping to accomplish.

Add a couple of comments. Use variable names that mean something. Use the
assertion failure description parameters when possible. Nobody's code is as
self-documenting as they believe it to be.

```javascript

// NOT AWESOME
// this test forces the next victim to have to
// read every single line of source code you wrote
it("should work", async () => {
    let thing = await svc.loadHistories();
    assert(thing);
})

// BETTER
// With this test, you can just read at the errors on the mocha 
// test output to have a pretty good idea of what went sour.
it("should have resolved to an array of integer IDs", async () => {
    let historyIds = await historyService.loadHistories();
    assert(historyIds, "History service should have had a result");
    assert(historyIds instanceof Array, "History results should have been an array");
    assert(historyIds.length == 4, "History call should have returned 4 ids");
})

```


### Only test the public API that you define (carefully!)

Internal implementations come and go with library upgrades and new tech. But
the point of the unit test is to make sure your units work as designed....
which means you need to... you know... design your code to work in units.

Separate your concerns and identify the developer-facing methods and functions
you expect them to use. Test THOSE. Everything else should probably be
considered an implementation detail.

Assume nobody cares *how* your code works, we just need to know that the public
API you designed *does* work. If performance problems or new tech necessitate a
re-write, these tests become a guide for the next implementation.


### Wrap native browser resources in a function so they can be easily mocked

If your javascript needs to talk to the window object, or navigator, etc. wrap
that in a function call so that it can be easily mocked during testing.

```javascript

// myModule.js

// ... other code

export function redirectTo(url) {
    window.location = url;
}


// myModule.test.js

import { __RewireAPI__ as myModuleRewire} from "./myModule";

function fakeRedirect(url) {
    console.log(`I would have gone to: ${url}`);
}

describe("some module", () => {

    beforeEach(() => {
        myModuleRewire.__Rewire__("redirectTo", fakeRedirect);
    })

    // ....
})
```

### Implement logic in pure functions when possible

The more of your logic that is written in deterministic functions (i.e. no
side-effects, same inputs always result in same outputs) the easier it is to
test. Just load up the functions and supply suitable test inputs.

There is almost definitely no such thing as a well-written 1000 line function.
Most of whatever happened in that thing was probably deterministic and can be
broken up into easily testable chunks.


## Specific test scenarios & examples

[Mocking an imported dependency](https://github.com/galaxyproject/galaxy/blob/dev/client/galaxy/scripts/components/Tags/tagService.test.js)

[Testing async operations](https://github.com/galaxyproject/galaxy/blob/dev/client/galaxy/scripts/components/Tags/tagService.test.js)

[Testing a Vue component for expected rendering output](https://github.com/galaxyproject/galaxy/blob/dev/client/galaxy/scripts/components/Tags/StatelessTags.test.js)

[Firing an event against a shallow mounted vue component](https://github.com/galaxyproject/galaxy/blob/dev/client/galaxy/scripts/components/Tags/StatelessTags.test.js)


## The dirty secret about testing

It's good to have tests, but testing code isn't really about testing at all,
it's actually about software design. 

Maintainable software is testable software. If you can run a unit test on your
code, then that means you must have necessarily separated your code into
testable units and you will have almost definitely written better, more
modular, more easily manipulated code, and nobody will ever contemplate using
git-blame to figure out what went wrong.

Probably.
