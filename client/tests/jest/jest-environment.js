import JSDOMEnvironment from "jest-environment-jsdom";
import "jsdom-worker";

export default class CustomJSDOMEnvironment extends JSDOMEnvironment {
    constructor(...args) {
        super(...args);

        this.global.Worker = Worker;
    }
}
