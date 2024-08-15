import { updateHistoryItemsInBulk } from "@/api/histories";
import { type components } from "@/api/schema";

export type HistoryContentBulkOperationPayload = components["schemas"]["HistoryContentBulkOperationPayload"];

export async function updateHistoryItemsBulk(historyId: string, changes: HistoryContentBulkOperationPayload) {
    await updateHistoryItemsInBulk({ history_id: historyId, ...changes });
}
