import { defineStore } from "pinia";
import { ref, set } from "vue";

import { GalaxyApi, type HDASummary } from "@/api";
import { HistoryFilters } from "@/components/History/HistoryFilters";
import { filtersToQueryValues } from "@/components/History/model/queries";
import { errorMessageAsString } from "@/utils/simple-error";

const DEFAULT_FILTERS: Record<string, any> = { visible: true, deleted: false };

/**
 * Fetches compact dataset summaries. It caches the datasets for each filter text, for the current
 * history only.
 *
 * It is scoped to `historyId`, `historyUpdateTime` and `filterText`.
 *
 * **Note:** *This store does not track the current history - it is meant to be used in tandem with
 * the `useHistoryDatasets` composable*.
 */
export const useHistoryDatasetsStore = defineStore("historyDatasetsStore", () => {
    const cachedDatasetsForFilterText = ref<Record<string, HDASummary[]>>({});
    const errorMessage = ref<string | null>(null);
    const isFetching = ref<Record<string, boolean>>({});

    /** The current scope of the cached datasets, defined by history ID, update time, and filter text */
    const currentScope = ref<{ id: string; time: string; text: string } | null>(null);

    async function fetchDatasetsForFiltertext(historyId: string, historyUpdateTime?: string, filterText = "") {
        if (isFetching.value[filterText]) {
            return { data: [], error: null };
        }

        if (
            currentScope.value &&
            currentScope.value.id === historyId &&
            currentScope.value.time === historyUpdateTime &&
            currentScope.value.text === filterText
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
        currentScope.value = { id: historyId, time: historyUpdateTime || "", text: filterText };

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
