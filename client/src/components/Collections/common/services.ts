import { type components, fetcher } from "@/api/schema";

export type HistoryContentBulkOperationPayload = components["schemas"]["HistoryContentBulkOperationPayload"];

const putHistories = fetcher.path("/api/histories/{history_id}/contents/bulk").method("put").create();
export async function updateHistories(historyId: string, changes: HistoryContentBulkOperationPayload) {
    await putHistories({ history_id: historyId, ...changes });
}
