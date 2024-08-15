import "@testing-library/jest-dom";
import "@testing-library/jest-dom/jest-globals";

import Vue from "vue";

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
