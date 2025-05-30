<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { type SearchResult, searchWorkflow } from "@/components/Workflow/Editor/modules/search";
import { useWorkflowStores } from "@/composables/workflowStores";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

const currentQuery = ref("");

const searchEmpty = computed(() => currentQuery.value.trim() === "");

const { workflowId } = useWorkflowStores();

const results = ref<SearchResult[]>([]);

watch(
    () => currentQuery.value,
    () => {
        results.value = searchWorkflow(currentQuery.value, workflowId);
    }
);
</script>

<template>
    <ActivityPanel title="Search">
        <DelayedInput placeholder="search workflow" :delay="200" @change="(v) => (currentQuery = v)" />

        <div v-if="searchEmpty" class="search-help">
            <p>Type to search all steps and comments in the workflow graph.</p>
            <p>Use any of the following keywords to narrow your search:</p>
            <ul>
                <li>step</li>
                <li>input</li>
                <li>output</li>
                <li>comment</li>
            </ul>
        </div>

        <div v-else class="search-help">
            <span>Found {{ results.length }}.</span>
            <span v-if="results.length > 0">Click a result to view it in the workflow.</span>
        </div>

        <div class="result-list">
            <button v-for="result in results" :key="result.searchData.id">
                {{ result.searchData.prettyName }}
            </button>
        </div>
    </ActivityPanel>
</template>

<style lang="scss" scoped>
.search-help {
    margin-top: var(--spacing-3);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-2);

    p,
    ul {
        margin: 0;
        padding: 0;
    }

    ul {
        padding-left: var(--spacing-4);
    }
}
</style>
