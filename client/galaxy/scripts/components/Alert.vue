<template>
    <b-alert :variant="galaxyKwdToBootstrap" :show="showP" v-bind="$props">
        <slot> {{ message }} </slot>
    </b-alert>
</template>

<script>
export default {
    props: {
        message: {
            type: String,
            default: ""
        },
        status: {
            type: String,
            default: ""
        },
        variant: {
            type: String,
            default: "done"
        },
        dismissible: Boolean,
        dismissLabel: String,
        show: [Boolean, Number],
        fade: Boolean
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
                error: "danger"
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
        }
    }
};
</script>
