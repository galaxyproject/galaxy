<script setup lang="ts">
import { onMounted, ref } from "vue";

import { appendScriptStyle } from "@/utils/utils";
import { loadWebhooks, pickWebhook } from "@/utils/webhooks";

interface Props {
    type: string;
    toolId?: string;
    toolVersion?: string;
}

const props = withDefaults(defineProps<Props>(), {
    toolId: "",
    toolVersion: "",
});

const container = ref<HTMLElement | null>(null);
const webhookId = ref<string | null>(null);

onMounted(async () => {
    if (container.value) {
        container.value.setAttribute("tool_id", props.toolId);
        container.value.setAttribute("tool_version", props.toolVersion);
    }

    const webhooks = await loadWebhooks();
    if (webhooks.length > 0) {
        const model = pickWebhook(webhooks);
        webhookId.value = model.id;
        appendScriptStyle(model);
    }
});
</script>

<template>
    <div ref="container">
        <div v-if="webhookId" :id="webhookId"></div>
    </div>
</template>
