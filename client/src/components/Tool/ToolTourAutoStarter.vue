<script setup lang="ts">
/**
 * ToolTourAutoStarter Component
 *
 * Automatically generates and launches interactive tours for Galaxy tools.
 * Manages the complete lifecycle of tool tours including generation, dataset
 * preparation, and tour initialization.
 *
 * Features:
 * - Automatic tour generation from backend
 * - History item state monitoring
 * - Deferred tour launch until datasets are ready
 * - Error handling for failed dataset uploads
 * - Version-based tour caching
 * - URL parameter-driven tour activation
 *
 * @component ToolTourAutoStarter
 * @example
 * <ToolTourAutoStarter
 *   :tool-id="'seqtk_seq'"
 *   :tool-version="'1.4+galaxy0'"
 *   :start="true" />
 */

import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";

import { ERROR_STATES } from "@/api/jobs";
import { generateTour, type TourDetails } from "@/api/tours";
import { Toast } from "@/composables/toast";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useTourStore } from "@/stores/tourStore";
import { errorMessageAsString } from "@/utils/simple-error";

/**
 * Component props for ToolTourAutoStarter
 */
interface Props {
    /**
     * The ID of the tool for which to generate a tour
     * @type {string}
     */
    toolId: string;

    /**
     * The version of the tool
     * @type {string}
     */
    toolVersion: string;

    /**
     * Whether to start the tour automatically
     * Can be a boolean or string representation ("true"/"false", "1"/"0")
     * @type {boolean | string}
     */
    start: boolean | string;
}

const props = defineProps<Props>();

const tourStore = useTourStore();
const { toolGeneratedTours } = storeToRefs(tourStore);

const { currentHistoryId } = storeToRefs(useHistoryStore());
const historyItemsStore = useHistoryItemsStore();

/** Tracks whether a tour generation request is currently in progress */
const generatingTour = ref(false);
/** Tracks the last tool version that was processed to prevent duplicate generation */
const lastProcessedVersion = ref<string | null>(null);
/** Stores the generated tour data and associated history item IDs */
const tourGenerationResult = ref<{ tour: TourDetails; hids: number[] } | null>(null);

/**
 * Unique identifier for the generated tour
 * @returns {string} Tour ID in format "tool-generated-{toolId}-{toolVersion}"
 */
const generatedTourId = computed(() => `tool-generated-${props.toolId}-${props.toolVersion}`);

/**
 * Determines whether the tour should be started based on the start prop
 * Handles boolean values, string representations, and null/undefined
 * @returns {boolean} True if tour should start
 */
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

/**
 * States of all history items required by the generated tour
 * @returns {Record<string, string>} Map of history item IDs to their states
 */
const historyItemStates = computed(() => {
    if (!tourGenerationResult.value?.hids?.length || !currentHistoryId.value) {
        return {};
    }
    return historyItemsStore.getStatesForHids(currentHistoryId.value, tourGenerationResult.value.hids);
});

/**
 * Checks if all required history items have completed successfully
 * @returns {boolean} True when all history items are in 'ok' state
 */
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

/**
 * Checks if any required history items have failed
 * @returns {boolean} True if any history item is in an error state
 */
const hasFailedHistoryItems = computed(() => {
    if (!tourGenerationResult.value?.hids?.length) {
        return false;
    }
    return Object.values(historyItemStates.value).some((state) => state && ERROR_STATES.includes(state));
});

/**
 * Conditionally starts the tour if all preconditions are met
 * Checks for start prop, tool ID/version presence, and prevents duplicate generation
 * @returns {void}
 */
function maybeStartTour(): void {
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

/**
 * Initiates tour generation from the backend API
 * Handles tour data with or without required history items
 * @returns {void}
 */
function startToolTour(): void {
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

/**
 * Registers the generated tour in the store and launches it
 * Only proceeds if tour data is available
 * @returns {void}
 */
function initializeGeneratedTour(): void {
    if (!tourGenerationResult.value?.tour || !generatedTourId.value) {
        return;
    }
    toolGeneratedTours.value[generatedTourId.value] = tourGenerationResult.value.tour;
    tourStore.setTour(generatedTourId.value);
    resetTourGenerationState();
}

/**
 * Clears tour generation state and optionally resets version tracking
 * @param {boolean} [resetKey=false] - Whether to also clear the last processed version
 * @returns {void}
 */
function resetTourGenerationState(resetKey: boolean = false): void {
    tourGenerationResult.value = null;
    generatingTour.value = false;
    if (resetKey) {
        lastProcessedVersion.value = null;
    }
}

/** Initialize the tour once all required history items are ready */
watch(areHistoryItemsReady, (isReady) => {
    if (isReady) {
        initializeGeneratedTour();
    }
});

/** Handle failed history items by showing error and resetting state */
watch(hasFailedHistoryItems, (hasFailed) => {
    if (hasFailed) {
        Toast.error(
            "This tour uploads datasets that failed to be created. You can try generating the tour again.",
            "Failed to generate tour",
        );
        resetTourGenerationState(true);
    }
});

/** Re-initialize tour generation when tool or start parameter changes */
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
