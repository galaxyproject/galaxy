// Order matters: the Vue.extend hook has to be in place before bootstrap-vue
// is evaluated, so these two side-effect imports stay first.
import "./legacy-libraries";
import "./legacy-bootstrap-vue";

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { configureCompat } from "vue";

// Shared by the app entry and the unit test setup, so components run the same
// way in both. Don't use "suppress-warning" here: on a component that opts
// into MODE 3 (vue-multiselect, vue-router's RouterLink, ...), it turns the
// Vue 2 behavior back on rather than just silencing it.
configureCompat({
    MODE: 2,
    // Libraries that still call Vue.set / Vue.delete.
    GLOBAL_SET: true,
    GLOBAL_DELETE: true,
    // Compat treats any plain function used as a component as a Vue 2 async
    // component factory and calls it that way. Galaxy has none of those left,
    // and Vue 3 functional components (lucide icons) are plain functions.
    COMPONENT_ASYNC: false,
    // Vue 3 instance API for Galaxy code. legacy-libraries.js keeps these on
    // for the Vue 2 libraries' own components.
    INSTANCE_SCOPED_SLOTS: false,
    INSTANCE_ATTRS_CLASS_STYLE: false,
    INSTANCE_CHILDREN: false,
    INSTANCE_SET: false,
    INSTANCE_DELETE: false,
    INSTANCE_DESTROY: false,
    INSTANCE_EVENT_HOOKS: false,
    // Array watchers in Galaxy code that need to see in-place changes say
    // `deep: true` themselves.
    WATCH_ARRAY: false,
    // Enumerated attributes (contenteditable, draggable, spellcheck) render as
    // given; Galaxy binds them to booleans or "true"/"false" already.
    ATTR_ENUMERATED_COERCION: false,
    // A bound `false` renders as attr="false" instead of removing the attribute.
    // Galaxy binds ARIA state as "true"/"false" strings and leaves boolean
    // attributes like `disabled` to props or `null`.
    ATTR_FALSE_VALUE: false,
    // A render function gets the instance proxy as its first argument, not
    // Vue 2's `h`; import `h` from "vue" instead. Galaxy's SFCs compile to
    // Vue 3 render functions and never hit this, so only hand-written renders
    // (mostly test stubs) care. vue-json-pretty's compiled template reads
    // `_self._c`, so it's marked in components/Common/legacy/VueJsonPretty.js.
    RENDER_FUNCTION: false,
    // No Vue 2 vnode fields (`data`, `tag`, `componentOptions`, ...) or private
    // instance properties on Galaxy components.
    PRIVATE_APIS: false,
    // <TransitionGroup> renders no wrapper unless given a `tag`; Galaxy's all set one.
    TRANSITION_GROUP_ROOT: false,
    // v-model on a component binds `modelValue` / `update:modelValue`. Every
    // Galaxy v-model component uses that contract; bootstrap-vue keeps
    // value/input through legacy-libraries.js.
    COMPONENT_V_MODEL: false,
    // Vue 2 APIs Galaxy code no longer uses at all: beforeDestroy/destroyed,
    // `this` in prop defaults, numeric keyCode modifiers and Vue.config.keyCodes,
    // filters, Vue 2 directive hook names, and a non-function `data`. Only
    // bootstrap-vue still hits these, and legacy-libraries.js keeps them on there.
    // OPTIONS_DATA_FN is the exception: compat only checks it on the root app's
    // `data`, never per component, so it's global-only.
    OPTIONS_BEFORE_DESTROY: false,
    OPTIONS_DESTROYED: false,
    PROPS_DEFAULT_THIS: false,
    V_ON_KEYCODE_MODIFIER: false,
    CONFIG_KEY_CODES: false,
    FILTERS: false,
    CUSTOM_DIR: false,
    OPTIONS_DATA_FN: false,
});

// FontAwesomeIcon builds its <svg> from `attrs`. With MODE 2's
// INSTANCE_LISTENERS, `attrs` holds no `on*` listeners, so `@click` and other
// listeners on an icon would never reach the svg.
FontAwesomeIcon.compatConfig = { MODE: 3 };
