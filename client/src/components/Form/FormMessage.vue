<template>
    <GAlert class="mt-2" :variant="variant" :show="showAlert">
        {{ message | l }}
    </GAlert>
</template>
<script>
import GAlert from "@/component-library/GAlert.vue";

export default {
    components: {
        GAlert,
    },
    props: {
        message: {
            type: String,
            default: null,
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
    watch: {
        message(newMessage) {
            this.resetTimer();
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
