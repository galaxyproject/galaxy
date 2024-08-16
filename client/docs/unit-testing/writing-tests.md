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

### Mocking API calls

When testing components that make API calls, you should use [**Mock Service Worker**](https://mswjs.io/docs/getting-started/) in combination with [**openapi-msw**](https://github.com/christoph-fricke/openapi-msw?tab=readme-ov-file#openapi-msw).

If you want to know more about why MSW is a good choice for mocking API calls, you can read [this article](https://mswjs.io/docs/philosophy).

If your component makes an API call, for example to get a particular history, you can mock the response of the API call using the `useServerMock` composable in your test file.

```ts
import { useServerMock } from "@/api/client/__mocks__";

const { server, http } = useServerMock();

describe("MyComponent", () => {
    it("should do something with the history", async () => {
        // Mock the response of the API call
        server.use(
            http.get("/api/histories/{history_id}", ({ params, query, response }) => {
                // You can use logic to return different responses based on the request
                if (query.get("view") === "detailed") {
                    return response(200).json(TEST_HISTORY_DETAILED);
                }

                // Or simulate an error
                if (params.history_id === "must-fail") {
                    return response("5XX").json(EXPECTED_500_ERROR, { status: 500 });
                }

                return response(200).json(TEST_HISTORY_SUMMARY);
            })
        );

        // Your test code here
    });
});
```

Using this approach, it will ensure the type safety of the API calls and the responses. If you need to mock API calls that are not defined in the OpenAPI specs, you can use the `http.untyped` variant to mock any API route. Or define an untyped response for a specific route with `HttpResponse`. See the example below:

```ts
const catchAll = http.untyped.all("/resource/*", ({ params }) => {
    return HttpResponse.json(/* ... */);
});
```

For more information on how to use `openapi-msw`, you can check the [official documentation](https://github.com/christoph-fricke/openapi-msw?tab=readme-ov-file#handling-unknown-paths).
