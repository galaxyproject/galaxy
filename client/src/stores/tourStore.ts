import { defineStore } from "pinia";
import { ref, watch } from "vue";

import type { TourDetails } from "@/api/tours";
import { useUserLocalStorage } from "@/composables/userLocalStorage";

export const useTourStore = defineStore("tourStore", () => {
    /** Track what tour ID we are expecting, to prevent any unintended localStorage
     * reactivity problems */
    const localTourId = ref<string>("");

    const toolGeneratedTours = ref<Record<string, TourDetails>>({});

    const currentTour = useUserLocalStorage<{ id: string; step: number } | undefined>(
        "currently-active-tour",
        undefined,
    );

    function setTour(tourId: string | undefined, step = 0) {
        localTourId.value = tourId || "";
        if (tourId) {
            currentTour.value = { id: tourId, step };
        } else {
            currentTour.value = undefined;
        }
    }

    watch(
        () => currentTour.value?.id,
        (newVal, oldVal) => {
            if (newVal === oldVal) {
                return;
            }

            // If localStorage is setting a different tour than what we expect, ignore it
            const expectedTour = localTourId.value || undefined;
            if (expectedTour && newVal !== expectedTour && oldVal === expectedTour) {
                setTour(expectedTour);
            }
        },
        { immediate: true },
    );

    return {
        currentTour,
        setTour,
        /** This serves as a temp cache to store Tool Generated Tours */
        toolGeneratedTours,
    };
});
