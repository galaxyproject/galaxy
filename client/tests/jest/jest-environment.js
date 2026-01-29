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

        if (!this.global.HTMLDialogElement.prototype.showModal) {
            this.global.HTMLDialogElement.prototype.showModal = function () {
                this.open = true;
            };
        }

        // FIXME https://github.com/jsdom/jsdom/issues/3294
        if (!this.global.HTMLDialogElement.prototype.close) {
            this.global.HTMLDialogElement.prototype.close = function (returnValue) {
                this.open = false;
                this.returnValue = returnValue;
            };
        }
    }
}
