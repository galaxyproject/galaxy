import "@testing-library/jest-dom";
import "@testing-library/jest-dom/jest-globals";
import "fake-indexeddb/auto";

import { createApp } from "@vue/compat";
import failOnConsole from "jest-fail-on-console";

// not available in jsdom, mock it out
Element.prototype.scrollIntoView = jest.fn();

// Vue 3 with compat mode setup for tests
// In Vue 3, app-level configurations are set on app instances
// For Jest tests, we'll configure Vue 3 compat mode globally

// Mock Vue for compatibility with existing tests
jest.mock("vue", () => {
    const Vue = jest.requireActual("@vue/compat");
    // In Vue 3, there's no global config.productionTip
    // The compat build handles most Vue 2 patterns automatically
    return Vue;
});

/* still don't understand what was invoking the following, but nothing should,
and this makes the tag tests work correctly */
global.setImmediate = global.setTimeout;

// Always mock the following imports
jest.mock("@/composables/hashedUserId");
jest.mock("@/composables/userLocalStorage");

failOnConsole();
