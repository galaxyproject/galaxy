import { GalaxyApi } from "@/api";
import { purgeDataset, undeleteDataset } from "@/api/datasets";
import { rethrowSimple } from "@/utils/simple-error";

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
    const { data: nonPurgedHistories, error: nonPurgedHistoriesError } = await GalaxyApi().GET("/api/histories", {
        params: {
            query: {
                keys: itemSizeSummaryFields,
                q: ["deleted", "purged"],
                qv: ["None", "false"],
            },
        },
    });

    if (nonPurgedHistoriesError) {
        rethrowSimple(nonPurgedHistoriesError);
    }

    const { data: nonPurgedArchivedHistories, error: nonPurgedArchivedHistoriesError } = await GalaxyApi().GET(
        "/api/histories/archived",
        {
            params: {
                query: {
                    keys: itemSizeSummaryFields,
                    q: ["purged"],
                    qv: ["false"],
                },
            },
        }
    );

    if (nonPurgedArchivedHistoriesError) {
        rethrowSimple(nonPurgedArchivedHistoriesError);
    }

    const allHistoriesTakingStorageResponse = [
        ...(nonPurgedHistories as ItemSizeSummary[]),
        ...(nonPurgedArchivedHistories as ItemSizeSummary[]),
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

    const { data, error } = await GalaxyApi().GET("/api/datasets", {
        params: {
            query: {
                history_id: historyId,
                keys: itemSizeSummaryFields,
                limit,
                order: "size-dsc",
                q: q,
                qv: qv,
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }
    return data as unknown as ItemSizeSummary[];
}

export async function fetchObjectStoreContentsSizeSummary(objectStoreId: string, limit = 5000) {
    const { data, error } = await GalaxyApi().GET("/api/datasets", {
        params: {
            query: {
                keys: itemSizeSummaryFields,
                limit,
                order: "size-dsc",
                q: ["purged", "history_content_type", "object_store_id"],
                qv: ["false", "dataset", objectStoreId],
            },
        },
    });

    if (error) {
        rethrowSimple(error);
    }
    return data as unknown as ItemSizeSummary[];
}

export async function undeleteHistoryById(historyId: string): Promise<ItemSizeSummary> {
    const { data, error } = await GalaxyApi().POST("/api/histories/deleted/{history_id}/undelete", {
        params: {
            path: { history_id: historyId },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data as ItemSizeSummary;
}

export async function purgeHistoryById(historyId: string): Promise<PurgeableItemSizeSummary> {
    const { data, error } = await GalaxyApi().DELETE("/api/histories/{history_id}", {
        params: {
            path: { history_id: historyId },
            query: { purge: true },
        },
    });

    if (error) {
        rethrowSimple(error);
    }
    return data as PurgeableItemSizeSummary;
}

export async function undeleteDatasetById(datasetId: string): Promise<ItemSizeSummary> {
    const data = await undeleteDataset(datasetId);
    return data as unknown as ItemSizeSummary;
}

export async function purgeDatasetById(datasetId: string): Promise<PurgeableItemSizeSummary> {
    const data = await purgeDataset(datasetId);
    return data as unknown as PurgeableItemSizeSummary;
}
