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
});
