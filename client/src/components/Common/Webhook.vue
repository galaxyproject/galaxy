<script setup lang="ts">
import { onMounted, ref } from "vue";

import Webhooks from "@/utils/webhooks";

interface Props {
    type: string;
    toolId?: string;
}

const props = withDefaults(defineProps<Props>(), {
    toolId: undefined,
});

const webhook = ref(null);

onMounted(() => {
    new Webhooks.WebhookView({
        webhook,
        type: props.type,
        toolId: props.toolId,
    });
});
</script>

<template>
    <div id="webhook-view" ref="webhook" />
</template>
