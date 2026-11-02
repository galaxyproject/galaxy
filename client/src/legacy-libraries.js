// Vue 2 libraries (bootstrap-vue, vue-json-pretty 1.x, @handsontable/vue 2.x)
// keep compat's Vue 2 behavior for their own components, so compat-config.js
// can turn flags off for Galaxy code without breaking them.
//
// compat reads `instance.type.compatConfig` before the global config, but only
// for keys it has: a flag set `false` globally would fall through to a component
// marked only `{ MODE: 2 }`. So the marker lists every per-component flag as
// on, and these components keep Vue 2 behavior whatever the global config says.
// COMPONENT_ASYNC stays as the global config has it (off).
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
    if (definition && typeof definition === "object" && !definition.compatConfig) {
        definition.compatConfig = LEGACY_COMPAT_CONFIG;
    }
    return originalExtend.call(this, definition);
};
