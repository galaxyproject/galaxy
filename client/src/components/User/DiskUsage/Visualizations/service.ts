import { fetcher } from "@/schema/fetcher";

const _getHistories = fetcher.path("/api/histories").method("get").create();
const _getDatasets = fetcher.path("/api/datasets").method("get").create();
const _undeleteHistory = fetcher.path("/api/histories/deleted/{history_id}/undelete").method("post").create();
const _purgeHistory = fetcher.path("/api/histories/{history_id}").method("delete").create();
const _updateDataset = fetcher.path("/api/histories/{history_id}/contents/{type}s/{id}").method("put").create();
const _purgeDataset = fetcher.path("/api/histories/{history_id}/contents/{type}s/{id}").method("delete").create();

export interface ItemSizeSummary {
    id: string;
    name: string;
    size: number;
    deleted: boolean;
}

interface PurgeableItemSizeSummary extends ItemSizeSummary {
    purged: boolean;
}

const itemSizeSummaryFields = "id,name,size,deleted";

export async function getAllHistoriesSizeSummary() {
    const allHistoriesTakingStorageResponse = await _getHistories({
        keys: itemSizeSummaryFields,
        q: ["deleted", "purged"],
        qv: ["None", "false"],
    });
    return allHistoriesTakingStorageResponse.data as ItemSizeSummary[];
}

export async function getHistoryContentsSizeSummary(historyId: string, limit = 5000) {
    const response = await _getDatasets({
        history_id: historyId,
        keys: itemSizeSummaryFields,
        limit,
        order: "size-dsc",
        q: ["purged"],
        qv: ["false"],
    });
    return response.data as unknown as ItemSizeSummary[];
}

export async function undeleteHistory(historyId: string): Promise<ItemSizeSummary> {
    const response = await _undeleteHistory({ history_id: historyId });
    return response.data as unknown as ItemSizeSummary;
}

export async function purgeHistory(historyId: string): Promise<PurgeableItemSizeSummary> {
    const response = await _purgeHistory({ history_id: historyId, purge: true });
    return response.data as unknown as PurgeableItemSizeSummary;
}

export async function undeleteDataset(historyId: string, datasetId: string): Promise<ItemSizeSummary> {
    const response = await _updateDataset({ history_id: historyId, id: datasetId, type: "dataset", deleted: false });
    return response.data as unknown as ItemSizeSummary;
}

export async function purgeDataset(historyId: string, datasetId: string): Promise<PurgeableItemSizeSummary> {
    const response = await _purgeDataset({ history_id: historyId, id: datasetId, type: "dataset", purge: true });
    return response.data as unknown as PurgeableItemSizeSummary;
}
