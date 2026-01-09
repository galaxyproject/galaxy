import { configureCompat } from "vue";

// Configure Vue 3 compatibility mode
configureCompat({
    // MODE: 2 means Vue 2 compatibility mode
    MODE: 2,

    // Explicitly enable/disable specific compatibility flags
    // Most features are automatically enabled in MODE: 2
    // We'll progressively disable these as we migrate

    // Features that are Vue 3 only (not needed in compat mode)
    FEATURE_ID_INJECTION: false,
    FEATURE_PROD_HYDRATION_MISMATCH_DETAILS: false,

    // Common warnings to suppress initially
    GLOBAL_MOUNT: "suppress-warning",
    GLOBAL_EXTEND: "suppress-warning",
    GLOBAL_PROTOTYPE: "suppress-warning",
    GLOBAL_SET: "suppress-warning",
    GLOBAL_DELETE: "suppress-warning",
    GLOBAL_OBSERVABLE: "suppress-warning",
    GLOBAL_PRIVATE_UTIL: "suppress-warning",
    CONFIG_SILENT: "suppress-warning",
    CONFIG_DEVTOOLS: "suppress-warning",
    CONFIG_KEY_CODES: "suppress-warning",
    CONFIG_PRODUCTION_TIP: "suppress-warning",
    CONFIG_IGNORED_ELEMENTS: "suppress-warning",
    INSTANCE_SET: "suppress-warning",
    INSTANCE_DELETE: "suppress-warning",
    INSTANCE_DESTROY: "suppress-warning",
    INSTANCE_EVENT_EMITTER: "suppress-warning",
    INSTANCE_EVENT_HOOKS: "suppress-warning",
    INSTANCE_CHILDREN: "suppress-warning",
    INSTANCE_LISTENERS: "suppress-warning",
    INSTANCE_SCOPED_SLOTS: "suppress-warning",
    INSTANCE_ATTRS_CLASS_STYLE: "suppress-warning",
    OPTIONS_DATA_FN: "suppress-warning",
    OPTIONS_DATA_MERGE: "suppress-warning",
    OPTIONS_BEFORE_DESTROY: "suppress-warning",
    OPTIONS_DESTROYED: "suppress-warning",
    WATCH_ARRAY: "suppress-warning",
    V_ON_KEYCODE_MODIFIER: "suppress-warning",
    CUSTOM_DIR: "suppress-warning",
    ATTR_FALSE_VALUE: "suppress-warning",
    ATTR_ENUMERATED_COERCION: "suppress-warning",
    TRANSITION_GROUP_ROOT: "suppress-warning",
    COMPONENT_ASYNC: "suppress-warning",
    COMPONENT_FUNCTIONAL: "suppress-warning",
    COMPONENT_V_MODEL: "suppress-warning",
    RENDER_FUNCTION: "suppress-warning",
    FILTERS: "suppress-warning",
    PRIVATE_APIS: "suppress-warning",
});
