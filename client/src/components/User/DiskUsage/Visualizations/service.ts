import { datasetsFetcher, purgeDataset, undeleteDataset } from "@/api/datasets";
import { archivedHistoriesFetcher, deleteHistory, historiesFetcher, undeleteHistory } from "@/api/histories";

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
    const nonPurgedHistoriesResponse = await historiesFetcher({
        keys: itemSizeSummaryFields,
        q: ["deleted", "purged"],
        qv: ["None", "false"],
    });
    const nonPurgedArchivedHistories = await archivedHistoriesFetcher({
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

export async function fetchHistoryContentsSizeSummary(
    historyId: string,
    limit = 5000,
    objectStoreId: string | null = null
) {
    const q = ["purged", "history_content_type"];
    const qv = ["false", "dataset"];

    if (objectStoreId) {
        q.push("object_store_id");
        qv.push(objectStoreId);
    }

    const response = await datasetsFetcher({
        history_id: historyId,
        keys: itemSizeSummaryFields,
        limit,
        order: "size-dsc",
        q: q,
        qv: qv,
    });
    return response.data as unknown as ItemSizeSummary[];
}

export async function fetchObjectStoreContentsSizeSummary(objectStoreId: string, limit = 5000) {
    const response = await datasetsFetcher({
        keys: itemSizeSummaryFields,
        limit,
        order: "size-dsc",
        q: ["purged", "history_content_type", "object_store_id"],
        qv: ["false", "dataset", objectStoreId],
    });
    return response.data as unknown as ItemSizeSummary[];
}

export async function undeleteHistoryById(historyId: string): Promise<ItemSizeSummary> {
    const response = await undeleteHistory({ history_id: historyId });
    return response.data as unknown as ItemSizeSummary;
}

export async function purgeHistoryById(historyId: string): Promise<PurgeableItemSizeSummary> {
    const response = await deleteHistory({ history_id: historyId, purge: true });
    return response.data as unknown as PurgeableItemSizeSummary;
}

export async function undeleteDatasetById(datasetId: string): Promise<ItemSizeSummary> {
    const data = await undeleteDataset(datasetId);
    return data as unknown as ItemSizeSummary;
}

export async function purgeDatasetById(datasetId: string): Promise<PurgeableItemSizeSummary> {
    const data = await purgeDataset(datasetId);
    return data as unknown as PurgeableItemSizeSummary;
}
