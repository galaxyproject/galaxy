import "@testing-library/jest-dom";
import "@testing-library/jest-dom/jest-globals";
import "fake-indexeddb/auto";

import { createApp, configureCompat } from "@vue/compat";
import failOnConsole from "jest-fail-on-console";

// not available in jsdom, mock it out
Element.prototype.scrollIntoView = jest.fn();

// Vue 3 with compat mode setup for tests
// Configure Vue 3 compat mode to be more permissive for legacy components
configureCompat({
    // Enable all Vue 2 compatibility features globally for tests
    MODE: 2,
    GLOBAL_EXTEND: true,
    GLOBAL_MOUNT: true,
    RENDER_FUNCTION: true,
    COMPONENT_FUNCTIONAL: true,
    COMPONENT_V_MODEL: true,
    ATTR_FALSE_VALUE: true,
    ATTR_ENUMERATED_COERCION: true,
    TRANSITION_CLASSES: true,
    FILTERS: true,
    PRIVATE_APIS: true,
});

// In Vue 3, app-level configurations are set on app instances
// For Jest tests, we'll configure Vue 3 compat mode globally

// Mock Vue for compatibility with existing tests
jest.mock("vue", () => {
    const Vue = jest.requireActual("@vue/compat");
    // In Vue 3, there's no global config.productionTip
    // The compat build handles most Vue 2 patterns automatically
    return Vue;
});

// Suppress Vue 3 deprecation warnings during testing
const originalWarn = console.warn;
console.warn = jest.fn((msg) => {
    // Suppress specific Vue 3 deprecation warnings that don't affect test functionality
    if (
        msg.indexOf &&
        (msg.indexOf("[Vue warn]: (deprecation GLOBAL_EXTEND)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation GLOBAL_MOUNT)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation COMPONENT_FUNCTIONAL)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation FILTERS)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation PRIVATE_APIS)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation WATCH_ARRAY)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation RENDER_FUNCTION)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation COMPONENT_V_MODEL)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation GLOBAL_PRIVATE_UTIL)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation COMPONENT_ASYNC)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation GLOBAL_PROTOTYPE)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation CONFIG_OPTION_MERGE_STRATS)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation ATTR_FALSE_VALUE)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation OPTIONS_BEFORE_DESTROY)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation INSTANCE_LISTENERS)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation INSTANCE_SCOPED_SLOTS)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation INSTANCE_ATTRS_CLASS_STYLE)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation INSTANCE_EVENT_EMITTER)") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation OPTIONS_DATA_MERGE)") >= 0 ||
            msg.indexOf("[Vue Router warn]:") >= 0 ||
            (msg.indexOf("[Vue warn]: Component") >= 0 && msg.indexOf("has already been registered") >= 0) ||
            (msg.indexOf("[Vue warn]: Directive") >= 0 && msg.indexOf("has already been registered") >= 0) ||
            msg.indexOf("[Vue warn]: Failed to resolve component:") >= 0 ||
            msg.indexOf("[Vue warn]: Failed to resolve directive:") >= 0 ||
            msg.indexOf("[Vue warn]: Plugin has already been applied to target app.") >= 0 ||
            msg.indexOf("[Vue warn]: App already provides property with key") >= 0 ||
            msg.indexOf("[Vue warn]: (deprecation CONFIG_WHITESPACE)") >= 0 ||
            msg.indexOf("BootstrapVue warn") >= 0)
    ) {
        // Ignore these deprecation warnings during tests
        return;
    }
    // Pass through other warnings
    originalWarn(msg);
});

/* still don't understand what was invoking the following, but nothing should,
and this makes the tag tests work correctly */
global.setImmediate = global.setTimeout;

// Always mock the following imports
jest.mock("@/composables/hashedUserId");
jest.mock("@/composables/userLocalStorage");

failOnConsole();
