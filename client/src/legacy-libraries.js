// Vue 2 libraries (bootstrap-vue, vue-json-pretty 1.x, @handsontable/vue 2.x)
// keep compat's Vue 2 behavior for their own components, so compat-config.js
// can turn flags off for Galaxy code without breaking them.
//
// compat reads each key, MODE included, from `instance.type.compatConfig` when
// it's there and from the global config otherwise. With MODE 2, a flag is on
// unless the value it finds is `false`, so `{ MODE: 2 }` alone would only lose
// flags the global config sets to `false`. The marker lists every
// per-component flag as on anyway, so a global `false` added later can't reach
// these components. COMPONENT_ASYNC is left out on purpose: they take the
// global `false` for it.
import Vue from "vue";

const PER_COMPONENT_FLAGS = [
    "CONFIG_KEY_CODES",
    "INSTANCE_SET",
    "INSTANCE_DELETE",
    "INSTANCE_DESTROY",
    "INSTANCE_EVENT_EMITTER",
    "INSTANCE_EVENT_HOOKS",
    "INSTANCE_CHILDREN",
    "INSTANCE_LISTENERS",
    "INSTANCE_SCOPED_SLOTS",
    "INSTANCE_ATTRS_CLASS_STYLE",
    "OPTIONS_BEFORE_DESTROY",
    "OPTIONS_DESTROYED",
    "WATCH_ARRAY",
    "PROPS_DEFAULT_THIS",
    "V_ON_KEYCODE_MODIFIER",
    "CUSTOM_DIR",
    "ATTR_FALSE_VALUE",
    "ATTR_ENUMERATED_COERCION",
    "TRANSITION_GROUP_ROOT",
    "COMPONENT_FUNCTIONAL",
    "COMPONENT_V_MODEL",
    "RENDER_FUNCTION",
    "FILTERS",
    "PRIVATE_APIS",
];

export const LEGACY_COMPAT_CONFIG = Object.freeze({
    MODE: 2,
    ...Object.fromEntries(PER_COMPONENT_FLAGS.map((flag) => [flag, true])),
});

function componentOptions(component) {
    // Vue.extend constructors keep their options on `.options`.
    return typeof component === "function" && component.cid ? component.options : component;
}

// Mark a Vue 2 component and the components it registers locally.
export function legacyComponent(component, seen = new Set()) {
    const options = componentOptions(component);
    if (!options || typeof options !== "object" || seen.has(options)) {
        return component;
    }
    seen.add(options);
    if (!options.compatConfig) {
        options.compatConfig = LEGACY_COMPAT_CONFIG;
    }
    Object.values(options.components ?? {}).forEach((child) => legacyComponent(child, seen));
    return component;
}

// bootstrap-vue builds every component it has, exported or internal, through
// the Vue.extend it captures when its vue.js module is evaluated, so marking
// definitions on the way through reaches all of them. Galaxy code doesn't call
// Vue.extend. This module has to be evaluated before bootstrap-vue is:
// compat-config.js imports it first, and the galaxy-legacy-libraries-first
// plugin in vite.config.mjs covers the production chunking.
const originalExtend = Vue.extend;
Vue.extend = function legacyExtend(definition = {}) {
    return originalExtend.call(this, legacyComponent(definition));
};
