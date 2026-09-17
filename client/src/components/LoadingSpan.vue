<!--
    Galaxy's standard inline loading spinner. Use this for "this small thing is loading"
    UI states. For full-screen overlay loaders use LoadingOverlay; for button-with-spinner
    UI use Common/ButtonSpinner. Do not use bootstrap-vue's BSpinner -- migrate to this.
-->
<template>
    <span>
        <span :class="spinnerClasses" title="loading"></span>
        <span v-if="!spinnerOnly" class="loading-message" data-description="loading message">
            {{ message }}.<span class="blinking">..</span>
        </span>
    </span>
</template>
<script>
export default {
    name: "LoadingSpan",
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
