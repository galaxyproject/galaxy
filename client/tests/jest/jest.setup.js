import "@testing-library/jest-dom";

/* still don't understand what was invoking the following, but nothing should,
and this makes the tag tests work correctly */
global.XMLHttpRequest = undefined;

// stops Bootstrap's warnings when components can't find a non-existent doc
// https://github.com/bootstrap-vue/bootstrap-vue/issues/3303
process.env.BOOTSTRAP_VUE_NO_WARN = true;
