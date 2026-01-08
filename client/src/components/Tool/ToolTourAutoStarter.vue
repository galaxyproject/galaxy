<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";

import { ERROR_STATES } from "@/api/jobs";
import { generateTour, type TourDetails } from "@/api/tours";
import { Toast } from "@/composables/toast";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useTourStore } from "@/stores/tourStore";
import { errorMessageAsString } from "@/utils/simple-error";

interface Props {
    toolId: string;
    toolVersion: string;
    start: boolean | string;
}

const props = defineProps<Props>();

const tourStore = useTourStore();
const { toolGeneratedTours } = storeToRefs(tourStore);

const { currentHistoryId } = storeToRefs(useHistoryStore());
const historyItemsStore = useHistoryItemsStore();

const generatingTour = ref(false);
const tourGenerationResult = ref<{ tour: TourDetails; hids: number[] } | null>(null);
const lastProcessedVersion = ref<string | null>(null);

const generatedTourId = computed(() => `tool-generated-${props.toolId}-${props.toolVersion}`);

const shouldStartTour = computed(() => {
    if (props.start === undefined || props.start === null) {
        return false;
    }
    if (typeof props.start === "boolean") {
        return props.start;
    }
    const normalized = `${props.start}`.toLowerCase();
    return normalized !== "false" && normalized !== "0";
});

const historyItemStates = computed(() => {
    if (!tourGenerationResult.value?.hids?.length || !currentHistoryId.value) {
        return {};
    }
    return historyItemsStore.getStatesForHids(currentHistoryId.value, tourGenerationResult.value.hids);
});

const areHistoryItemsReady = computed(() => {
    if (!tourGenerationResult.value?.hids?.length) {
        return false;
    }
    const states = Object.values(historyItemStates.value);
    if (!states.length) {
        return false;
    }
    return states.every((state) => state && state === "ok");
});

const hasFailedHistoryItems = computed(() => {
    if (!tourGenerationResult.value?.hids?.length) {
        return false;
    }
    return Object.values(historyItemStates.value).some((state) => state && ERROR_STATES.includes(state));
});

function maybeStartTour() {
    if (!shouldStartTour.value) {
        return;
    }
    if (!props.toolId || !props.toolVersion) {
        return;
    }
    const versionKey = `${props.toolId}/${props.toolVersion}`;
    if (lastProcessedVersion.value === versionKey) {
        return;
    }
    lastProcessedVersion.value = versionKey;
    startToolTour();
}

function startToolTour() {
    if (generatingTour.value) {
        return;
    }
    generatingTour.value = true;
    generateTour(props.toolId, props.toolVersion)
        .then(({ tour, uploaded_hids, use_datasets }) => {
            const hids = use_datasets ? uploaded_hids : [];
            tourGenerationResult.value = { tour, hids };
            if (!hids.length) {
                initializeGeneratedTour();
            } else {
                Toast.info("This tour waits for history datasets to be ready.", "Please wait");
            }
        })
        .catch((error) => {
            Toast.error(errorMessageAsString(error) || "An unknown error occurred", "Failed to generate tour");
            resetTourGenerationState(true);
        });
}

function initializeGeneratedTour() {
    if (!tourGenerationResult.value?.tour || !generatedTourId.value) {
        return;
    }
    toolGeneratedTours.value[generatedTourId.value] = tourGenerationResult.value.tour;
    tourStore.setTour(generatedTourId.value);
    resetTourGenerationState();
}

function resetTourGenerationState(resetKey = false) {
    tourGenerationResult.value = null;
    generatingTour.value = false;
    if (resetKey) {
        lastProcessedVersion.value = null;
    }
}

// Initialize the tour once all required history items are ready
watch(areHistoryItemsReady, (isReady) => {
    if (isReady) {
        initializeGeneratedTour();
    }
});

// Handle failed history items by showing error and resetting state
watch(hasFailedHistoryItems, (hasFailed) => {
    if (hasFailed) {
        Toast.error(
            "This tour uploads datasets that failed to be created. You can try generating the tour again.",
            "Failed to generate tour",
        );
        resetTourGenerationState(true);
    }
});

// Re-initialize tour generation when tool or start parameter changes
watch(
    () => [props.toolId, props.toolVersion, shouldStartTour.value],
    () => {
        resetTourGenerationState(true);
        maybeStartTour();
    },
);

onMounted(() => {
    maybeStartTour();
});
</script>

<template>
    <span aria-hidden="true" />
</template>
