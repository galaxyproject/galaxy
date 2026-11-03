import type { HDASummary } from "@/api";

/** An ok, visible text dataset in `history-1`; ID-derived fields follow `overrides.id`. */
export function getFakeDatasetSummary(overrides: Partial<HDASummary> = {}): HDASummary {
    const id = overrides.id ?? "dataset-id";
    const historyId = overrides.history_id ?? "history-1";
    return {
        id,
        dataset_id: id,
        hid: 1,
        name: `dataset ${id}`,
        history_content_type: "dataset",
        history_id: historyId,
        url: `/api/histories/${historyId}/contents/${id}`,
        state: "ok",
        extension: "txt",
        genome_build: null,
        type: "file",
        tags: [],
        deleted: false,
        purged: false,
        visible: true,
        create_time: "2024-01-01T00:00:00",
        update_time: "2024-01-01T00:00:00",
        ...overrides,
    };
}
