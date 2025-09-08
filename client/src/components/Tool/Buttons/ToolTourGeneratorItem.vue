<script setup lang="ts">
import { faPuzzlePiece } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdownItem } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { generateTour, type TourDetails } from "@/api/tours";
import { Toast } from "@/composables/toast";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useTourStore } from "@/stores/tourStore";
import { errorMessageAsString } from "@/utils/simple-error";

import LoadingSpan from "@/components/LoadingSpan.vue";

const props = defineProps<{
    toolId: string;
    toolVersion: string;
}>();

const tourStore = useTourStore();
const { currentTour, toolGeneratedTours } = storeToRefs(tourStore);

const { currentHistoryId } = storeToRefs(useHistoryStore());

const historyItemsStore = useHistoryItemsStore();

const generatingTour = ref(false);
const localTourData = ref<{ tour: TourDetails; hids: number[] } | null>(null);

const generatedTourId = computed(() => `tool-generated-${props.toolId}-${props.toolVersion}`);

async function clickGenerateTour() {
    if (generatingTour.value) {
        return;
    }

    generatingTour.value = true;

    try {
        const { tour, uploaded_hids, use_datasets } = await generateTour(props.toolId, props.toolVersion);
        localTourData.value = { tour, hids: use_datasets ? uploaded_hids : [] };
        if (!uploaded_hids.length) {
            generatingTour.value = false;
        } else {
            Toast.info("This tour waits for history datasets to be ready.", "Please wait");
        }
    } catch (error) {
        Toast.error(errorMessageAsString(error) || "An unknown error occurred", "Failed to generate tour");
        generatingTour.value = false;
    }
}

const states = computed(() => {
    if (!currentHistoryId.value || localTourData.value === null) {
        return [];
    }
    const stateDict = historyItemsStore.getStatesForHids(currentHistoryId.value, localTourData.value.hids);
    return Object.values(stateDict);
});

const allStatesOk = computed(() => {
    if (localTourData.value?.hids.length && states.value.length === 0) {
        // If there are HIDs but no states, it means the history has not loaded these items yet
        return false;
    }

    return states.value.length === 0 || states.value.every((state) => state && state === "ok");
});

const waitedForItemsOk = computed<boolean>(() => localTourData.value !== null && allStatesOk.value);

watch(
    () => [waitedForItemsOk.value, localTourData.value],
    () => {
        if (waitedForItemsOk.value && localTourData.value !== null) {
            toolGeneratedTours.value[generatedTourId.value] = localTourData.value.tour;

            reset();

            Toast.success("You can now start the tour", "Tour is ready!");
            tourStore.setTour(generatedTourId.value);
        }
    },
);

function reset() {
    localTourData.value = null;
    generatingTour.value = false;
}
</script>

<template>
    <BDropdownItem
        v-if="!currentTour?.id"
        data-description="click to generate tour"
        :disabled="generatingTour"
        @click="clickGenerateTour">
        <span v-if="!generatingTour">
            <FontAwesomeIcon :icon="faPuzzlePiece" /><span v-localize>Generate Tour</span>
        </span>
        <LoadingSpan v-else message="Generating Tour" />
    </BDropdownItem>
</template>
