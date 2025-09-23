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

const displayText = computed(() => {
    if (contentState.value?.displayName) {
        return contentState.value.displayName;
    }

    const state = dataset.value?.state;
    return state ? state.replace(/_/g, " ") : "n/a";
});

const tooltipText = computed(() => contentState.value?.text || null);

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
