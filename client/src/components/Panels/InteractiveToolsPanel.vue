<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { getAppRoot } from "@/onload/loadConfig";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import type { Tool } from "@/stores/toolStore";
import { useToolStore } from "@/stores/toolStore";

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
                <button
                    v-for="tool in interactiveTools"
                    :key="tool.id"
                    class="tool-item"
                    @click="onToolClick(tool, $event)">
                    <div class="d-flex">
                        <div class="tool-icon mr-2">
                            <img
                                v-if="tool.icon"
                                :src="getAppRoot() + 'api/tools/' + tool.id + '/icon'"
                                alt="tool icon" />
                        </div>
                        <div class="text-break">
                            <div class="tool-list-title font-weight-bold">{{ tool.name }}</div>
                            <div class="tool-list-text text-muted">{{ tool.description }}</div>
                        </div>
                    </div>
                </button>
            </div>
        </div>
    </ActivityPanel>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.tool-item {
    background: none;
    border: none;
    text-align: left;
    transition: none;
    width: 100%;
    padding: 0.25rem;
    border-bottom: 1px solid #eee;

    &:hover {
        background: $gray-200;
    }

    &:last-child {
        border-bottom: none;
    }
}

.tool-icon {
    img {
        width: 3rem;
    }
}
</style>
