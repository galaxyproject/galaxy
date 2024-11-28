import "jsdom-worker";

import JSDOMEnvironment from "jest-fixed-jsdom";

class MockObserver {
    constructor(...args) {}

    observe(...args) {}
    unobserve(...args) {}
}

export default class CustomJSDOMEnvironment extends JSDOMEnvironment {
    constructor(...args) {
        super(...args);

        this.global.Worker = Worker;

        this.global.IntersectionObserver = MockObserver;

        // FIXME https://github.com/jsdom/jsdom/issues/3363
        this.global.structuredClone = structuredClone;
    }
}
