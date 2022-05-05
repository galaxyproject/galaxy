<template>
    <div id="webhook-view" ref="webhook" />
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
            type: this.type,
            toolId: this.toolId,
        });
    },
};
</script>
