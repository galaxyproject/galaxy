import { fetcher } from "@/schema/fetcher";

const getHistories = fetcher.path("/api/histories").method("get").create();
const getArchivedHistories = fetcher.path("/api/histories/archived").method("get").create();
const getDatasets = fetcher.path("/api/datasets").method("get").create();
const undeleteHistory = fetcher.path("/api/histories/deleted/{history_id}/undelete").method("post").create();
const purgeHistory = fetcher.path("/api/histories/{history_id}").method("delete").create();
const updateDataset = fetcher.path("/api/histories/{history_id}/contents/{type}s/{id}").method("put").create();
const purgeDataset = fetcher.path("/api/histories/{history_id}/contents/{type}s/{id}").method("delete").create();

export interface ItemSizeSummary {
    id: string;
    name: string;
    size: number;
    deleted: boolean;
    archived: boolean;
}

interface PurgeableItemSizeSummary extends ItemSizeSummary {
    purged: boolean;
}

const itemSizeSummaryFields = "id,name,size,deleted,archived";

export async function fetchAllHistoriesSizeSummary(): Promise<ItemSizeSummary[]> {
    const nonPurgedHistoriesResponse = await getHistories({
        keys: itemSizeSummaryFields,
        q: ["deleted", "purged"],
        qv: ["None", "false"],
    });
    const nonPurgedArchivedHistories = await getArchivedHistories({
        keys: itemSizeSummaryFields,
        q: ["purged"],
        qv: ["false"],
    });
    const allHistoriesTakingStorageResponse = [
        ...(nonPurgedHistoriesResponse.data as ItemSizeSummary[]),
        ...(nonPurgedArchivedHistories.data as ItemSizeSummary[]),
    ];
    return allHistoriesTakingStorageResponse;
}

export async function fetchHistoryContentsSizeSummary(historyId: string, limit = 5000) {
    const response = await getDatasets({
        history_id: historyId,
        keys: itemSizeSummaryFields,
        limit,
        order: "size-dsc",
        q: ["purged", "history_content_type"],
        qv: ["false", "dataset"],
    });
    return response.data as unknown as ItemSizeSummary[];
}

export async function undeleteHistoryById(historyId: string): Promise<ItemSizeSummary> {
    const response = await undeleteHistory({ history_id: historyId });
    return response.data as unknown as ItemSizeSummary;
}

export async function purgeHistoryById(historyId: string): Promise<PurgeableItemSizeSummary> {
    const response = await purgeHistory({ history_id: historyId, purge: true });
    return response.data as unknown as PurgeableItemSizeSummary;
}

export async function undeleteDatasetById(historyId: string, datasetId: string): Promise<ItemSizeSummary> {
    const response = await updateDataset({ history_id: historyId, id: datasetId, type: "dataset", deleted: false });
    return response.data as unknown as ItemSizeSummary;
}

export async function purgeDatasetById(historyId: string, datasetId: string): Promise<PurgeableItemSizeSummary> {
    const response = await purgeDataset({ history_id: historyId, id: datasetId, type: "dataset", purge: true });
    return response.data as unknown as PurgeableItemSizeSummary;
}
