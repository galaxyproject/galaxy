<script setup lang="ts">
import { computed, watch } from "vue";

import { useToolStore } from "@/stores/toolStore";

const toolStore = useToolStore();

interface ToolLinkProps {
    toolId: string;
    toolVersion: string;
}

const props = defineProps<ToolLinkProps>();

const toolName = computed(() => {
    if (props.toolId) {
        return toolStore.getToolNameById(props.toolId);
    }
    return "";
});

const toolLink = computed(() => {
    return `/root?tool_id=${props.toolId}&tool_version=${props.toolVersion}`;
});

watch(
    props,
    () => {
        if (props.toolId && !toolStore.getToolForId(props.toolId)) {
            toolStore.fetchToolForId(props.toolId);
        }
    },
    { immediate: true }
);
</script>

<template>
    <router-link :to="toolLink">
        <b>{{ toolName || toolId }}</b> (Galaxy Version {{ toolVersion }})
    </router-link>
</template>
