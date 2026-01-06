<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { storeToRefs } from "pinia";

import { ERROR_STATES } from "@/api/jobs";
import { generateTour, type TourDetails } from "@/api/tours";
import { Toast } from "@/composables/toast";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useTourStore } from "@/stores/tourStore";
import { errorMessageAsString } from "@/utils/simple-error";

const props = defineProps<{
    toolId: string;
    toolVersion: string;
    start: boolean | string;
}>();

const tourStore = useTourStore();
const { toolGeneratedTours } = storeToRefs(tourStore);

const { currentHistoryId } = storeToRefs(useHistoryStore());
const historyItemsStore = useHistoryItemsStore();

const generatingTour = ref(false);
const localTourData = ref<{ tour: TourDetails; hids: number[] } | null>(null);
const tourStartVersionKey = ref<string | null>(null);

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

const generatedTourStates = computed(() => {
    if (!localTourData.value?.hids?.length || !currentHistoryId.value) {
        return {};
    }
    return historyItemsStore.getStatesForHids(currentHistoryId.value, localTourData.value.hids);
});

const waitedForItemsOk = computed(() => {
    if (!localTourData.value?.hids?.length) {
        return false;
    }
    const states = Object.values(generatedTourStates.value);
    if (!states.length) {
        return false;
    }
    return states.every((state) => state && state === "ok");
});

const anyStateInvalid = computed(() => {
    if (!localTourData.value?.hids?.length) {
        return false;
    }
    return Object.values(generatedTourStates.value).some((state) => state && ERROR_STATES.includes(state));
});

watch(waitedForItemsOk, (value) => {
    if (value) {
        initializeGeneratedTour();
    }
});

watch(anyStateInvalid, (value) => {
    if (value) {
        Toast.error(
            "This tour uploads datasets that failed to be created. You can try generating the tour again.",
            "Failed to generate tour",
        );
        resetTourGenerationState(true);
    }
});

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

function maybeStartTour() {
    if (!shouldStartTour.value) {
        return;
    }
    if (!props.toolId || !props.toolVersion) {
        return;
    }
    const versionKey = `${props.toolId}/${props.toolVersion}`;
    if (tourStartVersionKey.value === versionKey) {
        return;
    }
    tourStartVersionKey.value = versionKey;
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
            localTourData.value = { tour, hids };
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
    if (!localTourData.value?.tour || !generatedTourId.value) {
        return;
    }
    toolGeneratedTours.value[generatedTourId.value] = localTourData.value.tour;
    tourStore.setTour(generatedTourId.value);
    resetTourGenerationState();
}

function resetTourGenerationState(resetKey = false) {
    localTourData.value = null;
    generatingTour.value = false;
    if (resetKey) {
        tourStartVersionKey.value = null;
    }
}
</script>

<template>
    <span aria-hidden="true" />
</template>
