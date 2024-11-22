import "@testing-library/jest-dom";
import "@testing-library/jest-dom/jest-globals";
import "fake-indexeddb/auto";

import Vue from "vue";

// not available in jsdom, mock it out
Element.prototype.scrollIntoView = jest.fn();

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
