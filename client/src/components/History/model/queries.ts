import type { components, HistoryItemSummary } from "@/api";
import { GalaxyApi } from "@/api";
import { createHistoryDatasetCollectionInstanceSimple } from "@/api/datasetCollections";
import type {
    HistoryReference,
    StorageOperationExecutePolicy,
    StorageOperationExecuteResponse,
    StorageOperationPreviewResponse,
    StorageOperationRunResponse,
} from "@/api/histories";
import { getStorageOperationRunStatus } from "@/api/histories";
import { rethrowSimple } from "@/utils/simple-error";

type BulkOperation = components["schemas"]["HistoryContentItemOperation"];
type HistoryContentItem = components["schemas"]["HistoryContentItem"];
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
    deleteParams: Partial<{ purge: boolean; recursive: boolean }> = {},
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
    history: HistoryReference,
    operation: BulkOperation,
    filters: QueryFilters,
    items: HistoryContentItem[] = [],
    params = null,
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

export async function createDatasetCollection(history: HistoryReference, inputs = {}) {
    const defaults = {
        collection_type: "list",
        copy_elements: true,
        name: "list",
        element_identifiers: [],
        fields: "auto",
        hide_source_items: true,
        history_id: history.id,
    };
    const payload = Object.assign({}, defaults, inputs);
    return createHistoryDatasetCollectionInstanceSimple(payload);
}

export async function bulkStoragePreview(
    history: HistoryReference,
    targetObjectStoreId: string,
    filters: QueryFilters,
    items: HistoryContentItem[] = [],
): Promise<StorageOperationPreviewResponse> {
    const { data, error } = await GalaxyApi().POST("/api/histories/{history_id}/contents/bulk/storage/preview", {
        params: {
            path: { history_id: history.id },
            query: filtersToQueryValues(filters),
        },
        body: {
            mode: "move",
            target_object_store_id: targetObjectStoreId,
            items,
        },
    });

    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function bulkStorageExecute(
    history: HistoryReference,
    snapshotId: string,
    executionPolicy: StorageOperationExecutePolicy = { skip_ineligible: true },
    notifyOnCompletion = true,
): Promise<StorageOperationExecuteResponse> {
    const { data, error } = await GalaxyApi().POST("/api/histories/{history_id}/contents/bulk/storage/execute", {
        params: {
            path: { history_id: history.id },
        },
        body: {
            snapshot_id: snapshotId,
            execution_policy: executionPolicy,
            notify_on_completion: notifyOnCompletion,
        },
    });

    if (error) {
        rethrowSimple(error);
    }
    return data;
}

export async function bulkStorageRunStatus(
    history: HistoryReference,
    runId: string,
): Promise<StorageOperationRunResponse> {
    return getStorageOperationRunStatus(history, runId);
}
