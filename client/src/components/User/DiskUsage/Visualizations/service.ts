import { fetcher } from "@/schema/fetcher";

const getHistories = fetcher.path("/api/histories").method("get").create();
const getDatasets = fetcher.path("/api/datasets").method("get").create();

export interface ItemSizeSummary {
    id: string;
    name: string;
    size: number;
    deleted: boolean;
}

const historySizeSummaryFields = "id,name,size,deleted";

export async function getAllHistoriesSizeSummary() {
    const activeHistoriesResponse = await getHistories({ keys: historySizeSummaryFields, deleted: false });
    const activeHistories = activeHistoriesResponse.data as ItemSizeSummary[];
    const deletedHistoriesResponse = await getHistories({ keys: historySizeSummaryFields, deleted: true });
    const deletedHistories = deletedHistoriesResponse.data as ItemSizeSummary[];
    return [...activeHistories, ...deletedHistories];
}

export async function getHistoryContentsSizeSummary(historyId: string, limit = 1000) {
    const response = await getDatasets({
        history_id: historyId,
        keys: historySizeSummaryFields,
        limit,
        order: "size-dsc",
    });
    console.log(response.data);
    return response.data as unknown as ItemSizeSummary[];
}
