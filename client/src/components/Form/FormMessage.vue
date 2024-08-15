<template>
    <b-alert class="mt-2" :variant="variant" :show="showAlert">
        {{ message | l }}
    </b-alert>
</template>
<script>
export default {
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
