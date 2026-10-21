<!--
    Galaxy's standard inline loading spinner. Use this for "this small thing is loading"
    UI states. For full-screen overlay loaders use LoadingOverlay; for button-with-spinner
    UI use Common/ButtonSpinner. Do not use bootstrap-vue's BSpinner -- migrate to this.
-->
<template>
    <span :role="insideLiveRegion ? null : 'status'">
        <span :class="spinnerClasses" title="loading" aria-hidden="true"></span>
        <span v-if="!spinnerOnly" class="loading-message" data-description="loading message"> {{ message }}... </span>
        <span v-else class="sr-only">{{ message }}...</span>
    </span>
</template>
<script>
import { liveRegionKey } from "@galaxyproject/galaxy-ui";

export default {
    name: "LoadingSpan",
    inject: {
        insideLiveRegion: { from: liveRegionKey, default: false },
    },
    props: {
        classes: {
            type: String,
            required: false,
            default: null,
        },
        message: {
            type: String,
            default: "Loading",
        },
        spinnerOnly: {
            type: Boolean,
            required: false,
            default: false,
        },
    },
    computed: {
        spinnerClasses() {
            return ["loading-icon", "fa", "fa-spinner", "fa-spin"].concat(this.classes ? this.classes.split(" ") : []);
        },
    },
};
</script>
