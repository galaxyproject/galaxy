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
                    releaseLock() {}
                };
            }
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
                    releaseLock() {}
                };
            }
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

// Store original MutationObserver to wrap it with error handling
const OriginalMutationObserver = global.MutationObserver;

// Wrap MutationObserver to catch errors from vue2-teleport after tests complete
global.MutationObserver = class WrappedMutationObserver extends OriginalMutationObserver {
    constructor(callback) {
        const wrappedCallback = (mutations, observer) => {
            try {
                callback(mutations, observer);
            } catch (error) {
                // Silently ignore errors from vue2-teleport after tests are done
                // These errors occur when teleport tries to access DOM elements that no longer exist
                if (error.message && error.message.includes("querySelector") && 
                    error.stack && error.stack.includes("teleport")) {
                    // Ignore teleport-related querySelector errors
                    return;
                }
                // Re-throw other errors
                throw error;
            }
        };
        super(wrappedCallback);
    }
};

// Clean up after each test to prevent async operations from interfering
afterEach(() => {
    // Clear all timers
    jest.clearAllTimers();
    
    // Wait a tick to allow any pending DOM mutations to complete
    return new Promise(resolve => setImmediate(resolve));
});

// Always mock the following imports
jest.mock("@/composables/hashedUserId");
jest.mock("@/composables/userLocalStorage");

failOnConsole();
