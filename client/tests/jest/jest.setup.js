import "@testing-library/jest-dom";
import "@testing-library/jest-dom/jest-globals";
import "fake-indexeddb/auto";

import failOnConsole from "jest-fail-on-console";
import Vue from "vue";

// not available in jsdom, mock it out
Element.prototype.scrollIntoView = jest.fn();

// Polyfill BroadcastChannel for MSW support in jest environment
global.BroadcastChannel = class BroadcastChannel {
    constructor(name) {
        this.name = name;
    }
    postMessage() {}
    close() {}
    addEventListener() {}
    removeEventListener() {}
};

// Polyfill TransformStream for MSW support in jest environment
global.TransformStream = class TransformStream {
    constructor() {
        this.readable = {
            getReader() {
                return {
                    read() {
                        return Promise.resolve({ done: true });
                    },
                    releaseLock() {},
                };
            },
        };
        this.writable = {
            getWriter() {
                return {
                    write() {
                        return Promise.resolve();
                    },
                    close() {
                        return Promise.resolve();
                    },
                    releaseLock() {},
                };
            },
        };
    }
};

// Set Vue to suppress production / devtools / etc. warnings
Vue.config.productionTip = false;
Vue.config.devtools = false;

// if we do jest.mock(module) where modules imports Vue, it will create a clean Vue context
// that ignores the above tips. So pre-emptively mock out Vue in these contexts with the following
// block of code. GridList.test.js is a good example of this, when ran (yarn test GridList.test.js)
// it will bypass the attempt to set the Vue config values above and print the messages anyway without
// this block.
jest.mock("vue", () => {
    const Vue = jest.requireActual("vue"); // Import the actual Vue instance
    Vue.config.productionTip = false; // Disable production tip
    Vue.config.devtools = false; // Disable vue devtools
    return Vue; // Return the modified Vue instance
});

/* still don't understand what was invoking the following, but nothing should,
and this makes the tag tests work correctly */
global.setImmediate = global.setTimeout;

// Always mock the following imports
jest.mock("@/composables/hashedUserId");
jest.mock("@/composables/userLocalStorage");

// Filter out specific vue2-teleport errors before failOnConsole processes them
// These are harmless cleanup errors that occur after tests complete
const originalConsoleError = console.error;
console.error = (...args) => {
    const errorArg = args[0];

    // Check if this is the specific vue2-teleport querySelector error
    if (
        errorArg &&
        typeof errorArg === "object" &&
        errorArg.detail &&
        errorArg.detail.message &&
        errorArg.detail.message.includes("Cannot read properties of undefined (reading 'querySelector')") &&
        errorArg.detail.stack &&
        errorArg.detail.stack.includes("teleport.umd.js")
    ) {
        // This is the harmless vue2-teleport cleanup error - don't pass it to failOnConsole
        return;
    }

    // For all other errors, use the original console.error (which failOnConsole will intercept)
    originalConsoleError.apply(console, args);
};

// Enable failOnConsole for all other console errors/warnings
failOnConsole();
