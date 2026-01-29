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
