import "jsdom-worker";

import JSDOMEnvironment from "jest-environment-jsdom";

export default class CustomJSDOMEnvironment extends JSDOMEnvironment {
    constructor(...args) {
        super(...args);

        this.global.Worker = Worker;

        // FIXME https://github.com/jsdom/jsdom/issues/3363
        this.global.structuredClone = structuredClone;
    }
}
