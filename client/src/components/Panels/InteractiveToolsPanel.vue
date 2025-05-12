<script setup lang="ts">
import { faStop, faTools } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { getAppRoot } from "@/onload/loadConfig";
import { useEntryPointStore } from "@/stores/entryPointStore";
import { useInteractiveToolsStore } from "@/stores/interactiveToolsStore";
import type { Tool } from "@/stores/toolStore";
import { useToolStore } from "@/stores/toolStore";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import UtcDate from "@/components/UtcDate.vue";

const router = useRouter();
const toolStore = useToolStore();
const entryPointStore = useEntryPointStore();
const interactiveToolsStore = useInteractiveToolsStore();

// Get reactive refs from stores
const { entryPoints } = storeToRefs(entryPointStore);

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

    // Make sure we load active interactive tools
    await interactiveToolsStore.getActiveTools();
});

function onToolClick(tool: Tool, evt: Event) {
    evt.preventDefault();
    // encode spaces in tool.id
    router.push(`/?tool_id=${encodeURIComponent(tool.id)}&version=latest`);
}

function stopInteractiveTool(toolId: string, toolName: string) {
    interactiveToolsStore.stopInteractiveTool(toolId, toolName);
}

function openInteractiveTool(toolId: string) {
    router.push(`/interactivetool_entry_points/${toolId}/display`);
}
</script>

<template>
    <ActivityPanel title="Interactive Tools">
        <template v-slot:header>
            <div class="mb-1">
                <strong>Launch and manage interactive tools</strong>
            </div>
            <DelayedInput :delay="100" placeholder="Search interactive tools" @change="query = $event" />
        </template>

        <!-- Active Interactive Tools Section -->
        <div v-if="entryPoints.length > 0" class="active-tools-section mb-3">
            <h6 class="mt-2 mb-2">Active Interactive Tools</h6>
            <div class="active-tools-list">
                <div v-for="tool in entryPoints" :key="tool.id" class="active-tool-item">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <a :href="tool.target" class="tool-link" @click.prevent="openInteractiveTool(tool.id)">
                                {{ tool.name }}
                            </a>
                            <div class="text-muted small">
                                <span v-if="tool.active">Running</span>
                                <span v-else>Starting...</span>
                                | Created <UtcDate :date="tool.created_time" mode="elapsed" />
                            </div>
                        </div>
                        <button
                            class="btn btn-sm btn-link text-danger"
                            title="Stop this interactive tool"
                            @click="stopInteractiveTool(tool.id, tool.name)">
                            <FontAwesomeIcon :icon="faStop" />
                        </button>
                    </div>
                </div>
            </div>
            <hr />
        </div>

        <div>
            <div v-if="loading" class="p-3 text-center">
                <b-spinner label="Loading interactive tools..."></b-spinner>
                <p class="mt-2">Loading interactive tools...</p>
            </div>
            <div v-else-if="filteredTools.length === 0" class="p-3 text-center">
                <p>No matching interactive tools found</p>
            </div>
            <div v-else>
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
                            <FontAwesomeIcon v-else :icon="faTools" size="2x" />
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
    color: $gray-600;
    display: inline-block;
    width: 3rem;
    min-width: 3rem;
    height: 3rem;
    display: flex;
    align-items: center;
    justify-content: center;

    img {
        width: 3rem;
        max-height: 3rem;
    }
}

.active-tools-section {
    background-color: #f8f9fa;
    border-radius: 0.25rem;
    padding: 0.5rem;
}

.active-tool-item {
    padding: 0.5rem;
    border-bottom: 1px solid #eee;

    &:last-child {
        border-bottom: none;
    }

    &:hover {
        background: rgba(0, 0, 0, 0.03);
    }
}

.tool-link {
    font-weight: 500;
}
</style>
