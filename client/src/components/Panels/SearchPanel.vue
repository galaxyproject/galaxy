<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, watch } from "vue";

import { getIconForSearchData } from "@/components/Workflow/Editor/modules/itemIcons";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { SearchData, SearchResult } from "@/stores/workflowSearchStore";

import GButton from "@/components/BaseComponents/GButton.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

const currentQuery = ref("");

const searchEmpty = computed(() => currentQuery.value.trim() === "");

const { undoRedoStore, searchStore } = useWorkflowStores();

const results = ref<SearchResult[]>([]);

watch(
    () => [currentQuery.value, undoRedoStore.changeId],
    () => {
        if (!searchEmpty.value) {
            results.value = searchStore.searchWorkflow(currentQuery.value);
        } else {
            results.value = [];
        }
    },
);

const emit = defineEmits<{
    (e: "result-clicked", result: SearchData): void;
}>();
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

        <div v-else class="result-text">
            <span>Found {{ results.length }} result{{ results.length === 1 ? "" : "s" }} in workflow.</span>
            <span v-if="results.length > 0">Click a result to view it in the workflow.</span>
        </div>

        <div class="result-list">
            <GButton
                v-for="result in results"
                :key="result.searchData.id"
                outline
                class="result-button"
                @click="emit('result-clicked', result.searchData)">
                <FontAwesomeIcon fixed-width class="result-icon" :icon="getIconForSearchData(result.searchData)" />
                {{ result.searchData.prettyName }}
            </GButton>
        </div>
    </ActivityPanel>
</template>

<style lang="scss" scoped>
.result-text {
    margin-top: var(--spacing-3);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-1);
    margin-bottom: var(--spacing-2);
}

.result-list {
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-2);

    .result-button {
        text-align: start;
        align-items: start;

        .result-icon {
            margin-top: var(--spacing-1);
        }
    }
}

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
