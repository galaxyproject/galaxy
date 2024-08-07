import { type components, GalaxyApi, type HistoryItemSummary, type HistorySummary } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

type BulkOperation = components["schemas"]["HistoryContentItemOperation"];
type QueryFilters = Record<string, unknown>;

export function filtersToQueryValues(filters: QueryFilters) {
    const filterKeys = Object.keys(filters);
    const filterValues = filterKeys.map((key) => `${filters[key]}`);
    return { q: filterKeys, qv: filterValues };
}

/**
 * Deletes item from history
 */
export async function deleteContent(
    content: HistoryItemSummary,
    deleteParams: Partial<{ purge: boolean; recursive: boolean }> = {}
) {
    const defaults = { purge: false, recursive: false, stop_job: true };
    const params = Object.assign({}, defaults, deleteParams);
    const { data, error } = await GalaxyApi().DELETE("/api/histories/{history_id}/contents/{type}s/{id}", {
        params: {
            path: { history_id: content.history_id, type: content.history_content_type, id: content.id },
            query: params,
        },
    });

    if (error) {
        rethrowSimple(error);
    }
    return data;
}

/**
 * Update specific fields on datasets or collections.
 */
export async function updateContentFields(content: HistoryItemSummary, newFields = {}) {
    const { data, error } = await GalaxyApi().PUT("/api/histories/{history_id}/contents/{type}s/{id}", {
        params: {
            path: { history_id: content.history_id, type: content.history_content_type, id: content.id },
        },
        body: newFields,
    });

    if (error) {
        rethrowSimple(error);
    }
    return data;
}

/**
 * Performs an operation on a specific set of items or all the items
 * matching the filters.
 * If a specific set of items is provided, the filters are ignored, otherwise
 * the filters will determine which items are processed.
 */
export async function bulkUpdate(
    history: HistorySummary,
    operation: BulkOperation,
    filters: QueryFilters,
    items = [],
    params = null
) {
    const { data, error } = await GalaxyApi().PUT("/api/histories/{history_id}/contents/bulk", {
        params: {
            path: { history_id: history.id },
            query: filtersToQueryValues(filters),
        },
        body: {
            operation,
            items,
            params,
        },
    });

    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function createDatasetCollection(history: HistorySummary, inputs = {}) {
    const defaults = {
        collection_type: "list",
        copy_elements: true,
        name: "list",
        element_identifiers: [],
        hide_source_items: true,
    };
    const payload = Object.assign({}, defaults, inputs);

    const { data, error } = await GalaxyApi().POST("/api/histories/{history_id}/contents", {
        params: { path: { history_id: history.id } },
        body: { ...payload, instance_type: "history", type: "dataset_collection" },
    });

    if (error) {
        rethrowSimple(error);
    }
    return data;
}
