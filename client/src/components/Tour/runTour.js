import { storeToRefs } from "pinia";

import { useTourStore } from "@/stores/tourStore";

/**
 * Runs a Tour by identifier and provided data.
 *
 * Legacy method for webhooks that provide their own tour data. We simply set the tour
 * store with the `tourId` and cache the provided tour data, which `TourRunner.vue`
 * detects using the store.
 * @param {String} Unique Tour identifier (for api request)
 * @param {Object} Tour data
 * @returns mounted instance
 */
export async function runTour(tourId, tourData) {
    const tourStore = useTourStore();
    const { legacyTourCache } = storeToRefs(tourStore);

    legacyTourCache.value[tourId] = tourData;

    tourStore.setTour(tourId);
}
