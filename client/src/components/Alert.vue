<template>
    <b-alert :variant="galaxyKwdToBootstrap" :show="showP" v-bind="$props">
        <!-- @slot Message to display in alert -->
        <slot> {{ message }} </slot>
    </b-alert>
</template>

<script>
export default {
    props: {
        /**
         * Message to display in the alert
         */
        message: {
            type: String,
            default: "",
        },
        /**
         * Alias for variant, takes precedence if both are set
         */
        status: {
            type: String,
            default: "",
        },
        /**
         * Alert type, one of done/success, info, warning, error/danger
         */
        variant: {
            type: String,
            default: "done",
        },
        /** Display a close button in the alert that allows it to be dismissed */
        dismissible: Boolean,
        /** Label for the close button, for aria */
        dismissLabel: String,
        /** If a number, number of seconds to show before dismissing */
        show: [Boolean, Number],
        /** Should the alert fade out */
        fade: Boolean,
    },
    computed: {
        galaxyKwdToBootstrap() {
            let variant = this.variant;
            if (this.status !== "") {
                variant = this.status;
            }
            const galaxyKwdToBoostrapDict = {
                done: "success",
                info: "info",
                warning: "warning",
                error: "danger",
            };
            if (variant in galaxyKwdToBoostrapDict) {
                return galaxyKwdToBoostrapDict[variant];
            } else {
                return variant;
            }
        },
        showP() {
            if (this.show) {
                // explicit show prop overwrites all other checks
                return this.show;
            } else if (this.message !== "" || this.$slots.default) {
                // show if data is passed
                return true;
            } else {
                return false;
            }
        },
    },
};
</script>
