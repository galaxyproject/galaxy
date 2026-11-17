// Order matters: the Vue.extend hook has to be in place before bootstrap-vue
// is evaluated, so these two side-effect imports stay first.
import "./legacy-libraries";
import "./legacy-bootstrap-vue";

import { configureCompat } from "vue";

// Shared by the app entry and the unit test setup, so components run the same
// way in both.
//
// Galaxy code runs with Vue 3 semantics. The Vue 2 libraries (bootstrap-vue,
// vue-json-pretty 1.x, @handsontable/vue 2.x) are put back on MODE 2 for their
// own components by legacy-libraries.js. Most of what's left on here is what
// those libraries need where compat doesn't look at their component: global
// APIs (no component at all), plus COMPONENT_FUNCTIONAL and
// INSTANCE_EVENT_EMITTER, which compat checks on the Galaxy component around
// them. The last two settings have their own reasons, given below.
// TRANSITION_CLASSES is global-only too but stays off; multiselect.scss adds
// the Vue 3 class names vue-multiselect's CSS is missing. Don't turn any
// other per-component flag on here: a global `true` also reaches the Vue 3
// libraries that opt in with only `{ MODE: 3 }` (vue-multiselect, vue-router's
// RouterLink, ...).
configureCompat({
    MODE: 3,
    // bootstrap-vue builds every one of its components with Vue.extend.
    GLOBAL_EXTEND: true,
    // bootstrap-vue instantiates components with `new`: its modal manager at
    // import, and the tooltip, popover and dropdown helpers at runtime.
    GLOBAL_MOUNT: true,
    // Some bootstrap-vue components (BLink, BFormInput, ...) get its listeners
    // mixin's `bvListeners` data object twice and rely on Vue 2 deep-merging it.
    OPTIONS_DATA_MERGE: true,
    // Checked on the rendering parent, so a Galaxy component that renders
    // bootstrap-vue's functional components (BRow, BCol, BCard, BBadge, ...)
    // needs it for them to render at all.
    COMPONENT_FUNCTIONAL: true,
    // bootstrap-vue's listen-on-root and dropdown mixins call $root.$on/$off,
    // and the root is Galaxy's app (or the test mount).
    INSTANCE_EVENT_EMITTER: true,
    // Changes nothing: compat compiles runtime templates with whitespace
    // "preserve" either way, and only unit-test stubs have runtime templates.
    // Off, compat logs an error for each such stub, which fails the test.
    CONFIG_WHITESPACE: true,
    // Compat treats any plain function used as a component as a Vue 2 async
    // component factory. MODE 3 already has this off for Galaxy; it's listed so
    // the MODE 2 library components don't fall back to on, since a plain
    // function is a Vue 3 functional component (lucide icons) in their slots too.
    COMPONENT_ASYNC: false,
});
