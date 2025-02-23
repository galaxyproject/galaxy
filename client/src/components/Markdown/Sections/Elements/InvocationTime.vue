<script setup lang="ts">
import axios from "axios";
import { ref, watch } from "vue";

import { getAppRoot } from "@/onload/loadConfig";

const props = defineProps<{
    invocationId: string;
}>();

const invocationTime = ref();

async function fetchInvocation(invocationId: string) {
    try {
        const { data } = await axios.get(`${getAppRoot()}api/invocations/${invocationId}`);
        if (data.create_time) {
            invocationTime.value = new Date(data.create_time).toUTCString();
        }
    } catch (error) {
        console.error("Error fetching invocation time:", error);
        invocationTime.value = "";
    }
}

watch(
    () => props.invocationId,
    () => fetchInvocation(props.invocationId),
    { immediate: true }
);
</script>

<template>
    <div class="invocation-time">
        <pre><code>{{ invocationTime }}</code></pre>
    </div>
</template>
