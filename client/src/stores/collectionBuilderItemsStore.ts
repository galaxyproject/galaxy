import { defineStore } from "pinia";
import { ref, set } from "vue";

import { GalaxyApi, type HDASummary } from "@/api";
import { HistoryFilters } from "@/components/History/HistoryFilters";
import { filtersToQueryValues } from "@/components/History/model/queries";
import { errorMessageAsString } from "@/utils/simple-error";

const DEFAULT_FILTERS = { visible: true, deleted: false };

/**
 * Fetches datasets for the Collection Builder modal. It caches the datasets for each filter text.
 */
export const useCollectionBuilderItemsStore = defineStore("collectionBuilderItemsStore", () => {
    const cachedDatasetsForFilterText = ref<Record<string, HDASummary[]>>({});
    const errorMessage = ref<string | null>(null);
    const isFetching = ref<Record<string, boolean>>({});
    const lastFetch = ref<{ id: string; time: string; text: string } | null>(null);

    async function fetchDatasetsForFiltertext(historyId: string, historyUpdateTime?: string, filterText = "") {
        if (isFetching.value[filterText]) {
            return { data: [], error: null };
        }

        if (
            lastFetch.value &&
            lastFetch.value.id === historyId &&
            lastFetch.value.time === historyUpdateTime &&
            lastFetch.value.text === filterText
        ) {
            return {
                data: cachedDatasetsForFilterText.value[filterText] || [],
                error: errorMessage.value,
            };
        }

        set(isFetching.value, filterText, true);

        const filterQuery = getFilterQuery(filterText);

        // Note: Had "/api/histories/{history_id}/contents/datasets" before but it was returning datasets and collections
        const { data, error: apiError } = await GalaxyApi().GET("/api/histories/{history_id}/contents", {
            params: {
                path: { history_id: historyId },
                query: { ...filterQuery, v: "dev" },
            },
        });
        const returnedData = data as HDASummary[];

        let error = null;
        if (apiError) {
            error = errorMessageAsString(apiError);
            errorMessage.value = error;
        } else {
            set(cachedDatasetsForFilterText.value, filterText, returnedData);
        }

        set(isFetching.value, filterText, false);
        lastFetch.value = { id: historyId, time: historyUpdateTime || "", text: filterText };

        return { data: returnedData, error };
    }

    function getFilterQuery(filterText: string) {
        let filters = filterText ? HistoryFilters.getQueryDict(filterText) : DEFAULT_FILTERS;
        if (filters.history_content_type) {
            delete filters.history_content_type;
        }
        filters = { ...filters, history_content_type: "dataset" };
        return filtersToQueryValues(filters);
    }

    return {
        cachedDatasetsForFilterText,
        isFetching,
        fetchDatasetsForFiltertext,
    };
});
