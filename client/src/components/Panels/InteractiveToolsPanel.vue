<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { getAppRoot } from "@/onload/loadConfig";
import type { Tool } from "@/stores/toolStore";
import { useToolStore } from "@/stores/toolStore";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

const router = useRouter();
const toolStore = useToolStore();
const interactiveTools = ref<Tool[]>([]);
const loading = ref(true);
const query = ref("");

const filteredTools = computed(() => {
    const queryLower = query.value.toLowerCase();
    return interactiveTools.value.filter(
        (tool) =>
            !query.value ||
            tool.name.toLowerCase().includes(queryLower) ||
            (tool.description && tool.description.toLowerCase().includes(queryLower))
    );
});

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
            <DelayedInput :delay="100" placeholder="Search interactive tools" @change="query = $event" />
        </template>

        <div>
            <div v-if="loading" class="p-3 text-center">
                <b-spinner label="Loading interactive tools..."></b-spinner>
                <p class="mt-2">Loading interactive tools...</p>
            </div>
            <div v-else-if="filteredTools.length === 0" class="p-3 text-center">
                <p>No matching interactive tools found</p>
            </div>
            <div v-else class="p-2">
                <button
                    v-for="tool in filteredTools"
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
                            <div class="font-weight-bold">{{ tool.name }}</div>
                            <div class="text-muted">{{ tool.description }}</div>
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
    width: 100%;
    margin-bottom: 0.5rem;

    &:hover {
        background: $gray-200;
    }

    &:last-child {
        margin-bottom: none;
    }
}

.tool-icon {
    img {
        width: 3rem;
    }
}
</style>
