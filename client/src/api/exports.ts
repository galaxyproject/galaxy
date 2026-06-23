import { GalaxyApi, type ObjectExportTaskResponse } from "@/api";
import { ExportRecordModel } from "@/components/Common/models/exportRecordModel";
import { rethrowSimple } from "@/utils/simple-error";

import type { components } from "./schema";

export type WriteStoreToPayload = components["schemas"]["WriteStoreToPayload"];

/**
 * Gets a list of recent export records for the current user.
 * This includes exports to remote file sources (not short-term storage downloads).
 * @param limit Maximum number of exports to return
 * @param days Number of days to look back
 * @returns A promise with a list of export records for the current user.
 */
export async function fetchUserExportRecords(limit = 50, days = 30) {
    const { data, error } = await GalaxyApi().GET("/api/exports", {
        params: {
            query: { limit, days },
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    return data.map((item: ObjectExportTaskResponse) => new ExportRecordModel(item));
}
