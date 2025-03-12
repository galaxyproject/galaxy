<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import type { Tool } from "@/stores/toolStore";
import { useToolStore } from "@/stores/toolStore";

import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

const router = useRouter();

const toolStore = useToolStore();
const interactiveTools = ref<Tool[]>([]);

onMounted(async () => {
    await toolStore.fetchTools();
    interactiveTools.value = toolStore.getInteractiveTools();
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
            <div v-if="interactiveTools.length === 0" class="p-3">Loading interactive tools...</div>
            <div v-else class="tool-list-container p-2">
                <div v-for="tool in interactiveTools" :key="tool.id" class="tool-item p-2 mb-2 border rounded">
                    <h4>{{ tool.name }}</h4>
                    <p v-if="tool.description">{{ tool.description }}</p>
                    <a
                        :href="`/?tool_id=${encodeURIComponent(tool.id)}&version=latest`"
                        class="btn btn-primary btn-sm"
                        @on-click="onToolClick(tool, $event)">
                        Launch
                    </a>
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
    background-color: #f8f9fa;
    transition: background-color 0.2s;
}

.tool-item:hover {
    background-color: #e9ecef;
}
</style>
