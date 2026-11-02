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
});

// FontAwesomeIcon builds its <svg> from `attrs`. With MODE 2's
// INSTANCE_LISTENERS, `attrs` holds no `on*` listeners, so `@click` and other
// listeners on an icon would never reach the svg.
FontAwesomeIcon.compatConfig = { MODE: 3 };
