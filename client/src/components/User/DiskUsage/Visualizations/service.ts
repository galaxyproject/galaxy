import { fetcher } from "@/schema/fetcher";

const getHistories = fetcher.path("/api/histories").method("get").create();
const getDatasets = fetcher.path("/api/datasets").method("get").create();
const undelete = fetcher.path("/api/histories/deleted/{history_id}/undelete").method("post").create();
const purge = fetcher.path("/api/histories/{history_id}").method("delete").create();

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
    const allHistoriesTakingStorageResponse = await getHistories({
        keys: itemSizeSummaryFields,
        q: ["deleted", "purged"],
        qv: ["None", "false"],
    });
    return allHistoriesTakingStorageResponse.data as ItemSizeSummary[];
}

export async function getHistoryContentsSizeSummary(historyId: string, limit = 5000) {
    const response = await getDatasets({
        history_id: historyId,
        keys: itemSizeSummaryFields,
        limit,
        order: "size-dsc",
        q: ["purged"],
        qv: ["false"],
    });
    console.log(response.data);
    return response.data as unknown as ItemSizeSummary[];
}

export async function undeleteHistory(historyId: string): Promise<ItemSizeSummary> {
    const response = await undelete({ history_id: historyId });
    return response.data as unknown as ItemSizeSummary;
}

export async function purgeHistory(historyId: string): Promise<PurgeableItemSizeSummary> {
    const response = await purge({ history_id: historyId, purge: true });
    return response.data as unknown as PurgeableItemSizeSummary;
}
