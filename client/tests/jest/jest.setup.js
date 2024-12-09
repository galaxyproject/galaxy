import "@testing-library/jest-dom";
import "@testing-library/jest-dom/jest-globals";
import "fake-indexeddb/auto";

import Vue from "vue";

// Set Vue to suppress production / devtools / etc. warnings
Vue.config.productionTip = false;
Vue.config.devtools = false;

/* still don't understand what was invoking the following, but nothing should,
and this makes the tag tests work correctly */
global.setImmediate = global.setTimeout;

// Consistent timezone for tests so we can compare date strings
process.env.TZ = "America/New_York";

// Always mock the following imports
jest.mock("@/composables/hashedUserId");
jest.mock("@/composables/userLocalStorage");
