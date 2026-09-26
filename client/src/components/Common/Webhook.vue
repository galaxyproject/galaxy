<script setup lang="ts">
import { nextTick, onMounted, ref } from "vue";

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

interface WebhookModel {
    id: string;
    type?: string[];
    weight?: number;
    activate?: boolean;
    script?: string;
    styles?: string;
}

const container = ref<HTMLElement | null>(null);
const webhookId = ref<string | null>(null);

onMounted(async () => {
    if (container.value) {
        container.value.setAttribute("tool_id", props.toolId);
        container.value.setAttribute("tool_version", props.toolVersion);
    }

    const webhooks = (await loadWebhooks(props.type)).filter(
        (webhook: WebhookModel) => webhook.activate && webhook.script,
    );
    if (webhooks.length > 0) {
        const model = pickWebhook(webhooks);
        webhookId.value = model.id;
        // Wait for the `#<webhookId>` mount point to render before injecting the
        // webhook script, which targets that element as soon as it executes.
        await nextTick();
        appendScriptStyle(model);
    }
});
</script>

<template>
    <div ref="container">
        <div v-if="webhookId" :id="webhookId"></div>
    </div>
</template>
