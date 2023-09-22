### Clearly document the intent of your test

Please remember that these tests are not _for_ you. They're for the people who
come after you. It will be a lot easier to modify, repair and upgrade your code
if they can figure out what you were originally hoping to accomplish. Try to
use as detailed 'expect' statements as possible -- overuse of 'toBeTruthy()'
for example, can hide the intent of your test.

Add a couple of comments. Use variable names that mean something. Nobody's
code is as self-documenting as they believe it to be.

### Only test the public API that you define

Internal implementations come and go with library upgrades and new tech. But
the point of the unit test is to make sure your units work as designed....
which means you need to... you know... design your code to work in units.

Separate your concerns and identify the developer-facing methods and functions
you expect them to use. Test THOSE. Everything else should probably be
considered an implementation detail.

The other side of the same coin is to test _only_ the unit in question. If your
component has a model that uses a service that touches Vuex, which then uses
Axios to fetch some data -- don't test all that at once. Break things apart and
mock functionality to isolate testing to units. End to end testing is a
separate thing that shouldn't be attempted using spec tests in Jest.

Assume nobody cares _how_ your code works, we just need to know that the public
API you designed _does_ work. If performance problems or new tech necessitate a
re-write, these tests become a guide for the next implementation.

### Writing a test file

Jest will try to test any file ending in "\*.test.js". Please place your test
files inside client/src folders right next to whatever files that they are
testing.

Jest has extensive documentation on the expect API, mocking, and more on the
[official docs page](https://jestjs.io/docs/en/getting-started.html), which will
be your best resource here.

```js static
// yourcode.test.js

import { things } from "./yourcode.js";

describe("some module you wrote", () => {
    let transientVariables;
    let serviceInstances;
    let testData;

    beforeEach(() => {
        // setup your code (if necessary)
    });

    afterEach(() => {
        // teardown your code (so it doesn't ruin the next test)
    });

    it("should do something or other", () => {
        expect(workflowNodeCount()).toBe(5);
    });
});
```

### Check out the Jest helper functions

We have created some [common helpers for common testing
scenarios](https://github.com/galaxyproject/galaxy/blob/dev/client/tests/jest/helpers.js).
