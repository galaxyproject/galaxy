<template>
    <span>
        <span :class="spinnerClasses"></span>
        <span class="loading-message">{{ message }}.<span class="blinking">..</span></span>
    </span>
</template>
<script>
export default {
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
    },
    computed: {
        spinnerClasses() {
            return ["loading-icon", "fa", "fa-spinner", "fa-spin"].concat(this.classes ? this.classes.split(" ") : []);
        },
    },
};
</script>
