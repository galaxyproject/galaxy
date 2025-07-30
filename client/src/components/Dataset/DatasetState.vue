<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

import { STATES } from "@/components/History/Content/model/states";
import { useDatasetStore } from "@/stores/datasetStore";

import GTooltip from "@/components/BaseComponents/GTooltip.vue";

const datasetStore = useDatasetStore();

const props = defineProps<{
    datasetId: string;
}>();

const dataset = computed(() => datasetStore.getDataset(props.datasetId));
const contentState = computed(() => {
    const state = dataset.value && dataset.value.state;
    return state && STATES[state] ? STATES[state] : null;
});
const contentCls = computed(() => {
    const status = contentState.value && contentState.value.status;
    if (!status) {
        return `alert-success`;
    } else {
        return `alert-${status}`;
    }
});

// Compute short display text - capitalize the state name
const displayText = computed(() => {
    if (!dataset.value) {
        return "n/a";
    }
    const state = dataset.value.state;
    if (!state) {
        return "n/a";
    }

    // Capitalize first letter and replace underscores with spaces
    return state.charAt(0).toUpperCase() + state.slice(1).replace(/_/g, " ");
});

// Get the full descriptive text for tooltip
const tooltipText = computed(() => {
    return contentState.value?.text || null;
});

// Ref for the state badge element
const stateBadgeRef = ref<HTMLElement | null>(null);
</script>

<template>
    <span v-if="dataset && contentState" ref="stateBadgeRef" class="rounded px-2 py-1 ml-2" :class="contentCls">
        <span v-if="contentState.icon" class="mr-1">
            <FontAwesomeIcon fixed-width :icon="contentState.icon" :spin="contentState.spin" />
        </span>
        {{ displayText }}

        <GTooltip v-if="tooltipText" :reference="stateBadgeRef" :text="tooltipText" />
    </span>
</template>
