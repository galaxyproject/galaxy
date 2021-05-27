<template>
    <div ref="webhook" id="webhook-view" />
</template>
<script>
import Webhooks from "mvc/webhooks";

export default {
    props: {
        type: {
            type: String,
            required: true,
        },
        toolId: {
            type: String,
            default: null,
        },
    },
    mounted() {
        const el = this.$refs["webhook"];
        new Webhooks.WebhookView({
            el,
            type: "tool",
            toolId: this.toolId,
        });
    },
};
</script>
