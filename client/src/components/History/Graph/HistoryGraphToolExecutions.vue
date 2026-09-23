<script setup lang="ts">
import { faBolt, faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { ref } from "vue";

import type { HistoryGraphNode } from "./historyGraphMapper";

import ToolExecutionJobs from "./ToolExecutionJobs.vue";

interface Props {
    /** Tool-execution graph nodes to list, in display order. */
    nodes: HistoryGraphNode[];
}

defineProps<Props>();

// Independent per-row expanded state — multiple sections can be open at once,
// mirroring the workflow invocation graph's collapsible step cards.
const expanded = ref(new Set<string>());

function toggle(id: string) {
    // Reassign so Vue picks up the change (Set mutations aren't reactive in Vue 2.7).
    const next = new Set(expanded.value);
    if (next.has(id)) {
        next.delete(id);
    } else {
        next.add(id);
    }
    expanded.value = next;
}

function isExpanded(id: string): boolean {
    return expanded.value.has(id);
}
</script>

<template>
    <div class="history-graph-tool-executions p-2">
        <BAlert v-if="nodes.length === 0" show variant="info" class="mb-0">
            No tool executions to show. Galaxy started capturing tool execution data with release 26.1.
        </BAlert>
        <template v-else>
            <div v-for="node in nodes" :key="node.id" class="ui-portlet-section mb-2">
                <div
                    class="portlet-header portlet-operations cursor-pointer unselectable d-flex align-items-center"
                    role="button"
                    tabindex="0"
                    @keyup.enter="toggle(node.id)"
                    @click="toggle(node.id)">
                    <span class="portlet-title-text">
                        <FontAwesomeIcon :icon="faBolt" class="mr-1" />
                        {{ node.label }}
                    </span>
                    <FontAwesomeIcon class="ml-auto" :icon="isExpanded(node.id) ? faChevronUp : faChevronDown" />
                </div>
                <div v-if="isExpanded(node.id)" class="portlet-content">
                    <ToolExecutionJobs v-if="node.data?.itemId" class="p-2" :tool-execution-id="node.data.itemId" />
                </div>
            </div>
        </template>
    </div>
</template>
