<script setup lang="ts">
import { faChevronRight, faSearch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, onMounted, ref, watch } from "vue";

import { provideScopedWorkflowStores } from "@/composables/workflowStores";
import { capitalizeFirstLetter } from "@/utils/strings";

import type { Rectangle } from "../Workflow/Editor/modules/geometry";

import GButton from "../BaseComponents/GButton.vue";
import GraphSearch from "../Workflow/GraphSearch.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";

const props = defineProps<{
    invocationId: string;
    workflowId: string;
    tab?: "steps" | "inputs" | "outputs";
}>();

const storeId = computed(() => `invocation-${props.invocationId}`);

provideScopedWorkflowStores(storeId);

const toggled = ref(false);

const currentQuery = ref("");

const canvasContainerEl = ref<HTMLElement | null>(null);

onMounted(() => {
    canvasContainerEl.value = document.getElementById("canvas-container");
});

watch(toggled, (val) => {
    if (val) {
        canvasContainerEl.value = document.getElementById("canvas-container");
    }
});

const buttonTitle = computed(() => {
    if (!props.tab) {
        return "Search Invocation Graph";
    } else {
        return `Search Invocation ${capitalizeFirstLetter(props.tab)}`;
    }
});

// reset query, and toggled when tab changes
watch(
    () => props.tab,
    () => {
        currentQuery.value = "";
        toggled.value = false;
    },
);

function onHighlightRegion(bounds: Rectangle) {
    // TODO: Implement the logic to highlight the region in the workflow graph based on the bounds
    console.log("Highlighting region:", bounds);
}
</script>

<template>
    <div class="search-container">
        <div class="d-flex align-items-center flex-gapx-1">
            <DelayedInput
                v-if="toggled"
                placeholder="search workflow"
                :expanded.sync="toggled"
                :delay="200"
                @change="(v) => (currentQuery = v)" />
            <GButton
                tooltip
                :title="toggled ? 'Close Search' : buttonTitle"
                :transparent="toggled"
                @click="toggled = !toggled">
                <FontAwesomeIcon :icon="toggled ? faChevronRight : faSearch" fixed-width />
            </GButton>
        </div>

        <Transition name="search-results">
            <div v-if="toggled && canvasContainerEl" class="workflow-invocation-search-results">
                <GraphSearch :current-query="currentQuery" @result-clicked="(data) => onHighlightRegion(data.bounds)" />
            </div>
        </Transition>
    </div>
</template>

<style lang="scss" scoped>
.search-container {
    position: relative;
}

.workflow-invocation-search-results {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: var(--spacing);
    background: var(--color-grey-100);
    border: 1px solid var(--color-grey-200);
    border-radius: var(--spacing-2);
    box-shadow: 0 4px 12px var(--color-grey-300);
    padding: var(--spacing-3);
    z-index: 9999;
    min-width: 280px;

    max-height: 50vh;
    overflow-y: auto;
}

.search-results-enter-active {
    animation: search-drop-in 0.2s ease;
}

.search-results-leave-active {
    transition:
        opacity 0.2s ease,
        transform 0.2s ease;
    transform-origin: top right;
}

.search-results-leave-to {
    opacity: 0;
    transform: translateY(-6px) scaleY(0.95);
}

@keyframes search-drop-in {
    from {
        opacity: 0;
        transform: translateY(-6px) scaleY(0.95);
    }
}
</style>
