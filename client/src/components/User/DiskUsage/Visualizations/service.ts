import { datasetsFetcher, purgeHistoryDataset, undeleteHistoryDataset } from "@/api/datasets";
import { archivedHistoriesFetcher, historiesFetcher, purgeHistory, undeleteHistory } from "@/api/histories";

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

export async function fetchHistoryContentsSizeSummary(historyId: string, limit = 5000) {
    const response = await datasetsFetcher({
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
    const data = await undeleteHistoryDataset(historyId, datasetId);
    return data as unknown as ItemSizeSummary;
}

export async function purgeDatasetById(historyId: string, datasetId: string): Promise<PurgeableItemSizeSummary> {
    const data = await purgeHistoryDataset(historyId, datasetId);
    return data as unknown as PurgeableItemSizeSummary;
}
