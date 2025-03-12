<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import type { Tool } from "@/stores/toolStore";
import { useToolStore } from "@/stores/toolStore";

import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import ToolComponent from "@/components/Panels/Common/Tool.vue";

const router = useRouter();
const toolStore = useToolStore();
const interactiveTools = ref<Tool[]>([]);
const loading = ref(true);

onMounted(async () => {
    await toolStore.fetchTools();
    interactiveTools.value = toolStore.getInteractiveTools();
    loading.value = false;
});

function onToolClick(tool: Tool, evt: Event) {
    evt.preventDefault();
    // encode spaces in tool.id
    router.push(`/?tool_id=${encodeURIComponent(tool.id)}&version=latest`);
}
</script>

<template>
    <ActivityPanel
        title="Interactive Tools"
        go-to-all-title="Active Interactive Tools"
        href="/interactivetool_entry_points/list">
        <template v-slot:header>
            <div class="mb-1">
                <strong>Launch and manage interactive tools</strong>
            </div>
        </template>

        <div class="tool-list">
            <div v-if="loading" class="p-3 text-center">
                <b-spinner label="Loading interactive tools..."></b-spinner>
                <p class="mt-2">Loading interactive tools...</p>
            </div>
            <div v-else-if="interactiveTools.length === 0" class="p-3 text-center">
                <p>No interactive tools available</p>
            </div>
            <div v-else class="tool-list-container p-2">
                <div v-for="tool in interactiveTools" :key="tool.id" class="tool-item">
                    <ToolComponent :tool="tool" @onClick="onToolClick" />
                </div>
            </div>
        </div>
    </ActivityPanel>
</template>

<style scoped>
.tool-list-container {
    max-height: calc(100vh - 200px);
    overflow-y: auto;
}

.tool-item {
    padding: 0.25rem;
    border-bottom: 1px solid #eee;
}

.tool-item:last-child {
    border-bottom: none;
}
</style>
