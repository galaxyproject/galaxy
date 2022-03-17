Part of making good code is making that code easy to test. 

### Implement logic in pure functions when possible

The more of your logic that is written in deterministic functions (i.e. no
side-effects, same inputs always result in same outputs) the easier it is to
test. Just load up the functions and supply suitable test inputs.

There is almost definitely no such thing as a well-written 1000 line function.
Most of whatever happened in that thing was probably deterministic and can be
broken up into easily testable chunks.


### Wrap native browser resources in a function so they can be easily mocked

If your javascript needs to talk to the window object, or navigator, etc. wrap
that in a function call so that it can be easily mocked during testing.


#### Your Module
```js static
// myModule.js

// ... other code

export function redirectTo(url) {
    window.location = url;
}

export function theThingYouReallyCareAbout() {
    .....
    redirectTo(somePlace);
    ....
}
```

#### Your test file
```js static
// myModule.test.js
import { theThingYouReallyCareAbout, redirectTo } from "./myModule";

// calling jest.mock on the appropriate import path wraps the exports and gives
// access to new testing methods like mockImplementation
jest.mock("./myModule");
redirectTo.mockImplementation((url) => {
    console.log(`I would have gone to: ${url}`);
});

// You are testing theThingYouReallyCareAbout, but that function needs
// to call a window.relocate, By wrapping redirectTo as a function it was easy to mock
// and avoid errors in your test, because native browser objects do not even exist
// in the unit-testing environment.
describe("theThingYouReallyCareAbout", () => {
    it("Performs a redirect when Foo is clicked"){
        const result = theThingYouReallyCareAbout(abc123);
        expect(result).toBe(1);
    }
});
```
