import "@testing-library/jest-dom";
import "@testing-library/jest-dom/jest-globals";

import Vue from "vue";

import { server } from "@/api/client/__mocks__/node";

// Set Vue to suppress production / devtools / etc. warnings
Vue.config.productionTip = false;
Vue.config.devtools = false;

/* still don't understand what was invoking the following, but nothing should,
and this makes the tag tests work correctly */
global.XMLHttpRequest = undefined;
global.setImmediate = global.setTimeout;

// Always mock the following imports
jest.mock("@/composables/hashedUserId");
jest.mock("@/composables/userLocalStorage");

beforeAll(() => {
    // Enable API mocking before all the tests.
    server.listen();
});

afterEach(() => {
    // Reset the request handlers between each test.
    // This way the handlers we add on a per-test basis
    // do not leak to other, irrelevant tests.
    server.resetHandlers();
});

afterAll(() => {
    // Finally, disable API mocking after the tests are done.
    server.close();
});
