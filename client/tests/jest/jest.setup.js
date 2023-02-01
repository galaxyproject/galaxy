import "@testing-library/jest-dom";
import Vue from "vue";

// Set Vue to suppress production / devtools / etc. warnings
Vue.config.productionTip = false;
Vue.config.devtools = false;

/* still don't understand what was invoking the following, but nothing should,
and this makes the tag tests work correctly */
global.XMLHttpRequest = undefined;
global.setImmediate = global.setTimeout;
