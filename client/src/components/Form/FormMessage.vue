<template>
    <b-alert :variant="variant" :show="showAlert">
        {{ message }}
    </b-alert>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {
        message: {
            type: String,
            required: true,
        },
        variant: {
            type: String,
            default: "info",
        },
        timeout: {
            type: Number,
            default: 3000,
        },
        persistent: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            showDismissable: false,
        };
    },
    watch: {
        message(newMessage) {
            this.resetTimer();
        },
    },
    computed: {
        showAlert() {
            if (this.message) {
                if (!this.persistent) {
                    return this.showDismissable;
                }
                return true;
            }
            return false;
        },
    },
    methods: {
        resetTimer() {
            if (this.message) {
                this.showDismissable = true;
                if (this.timer) {
                    clearTimeout(this.timer);
                }
                this.timer = setTimeout(() => {
                    this.showDismissable = false;
                }, this.timeout);
            }
        },
    },
};
</script>
