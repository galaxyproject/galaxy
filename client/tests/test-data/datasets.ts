import type { HDADetailed, HDASummary } from "@/api";

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

/** Detailed text dataset response; ID-derived fields follow `overrides.id`. */
export function getFakeDatasetDetails(overrides: Partial<HDADetailed> = {}): HDADetailed {
    const summary = getFakeDatasetSummary(overrides);
    return {
        ...summary,
        accessible: true,
        annotation: null,
        api_type: "file",
        type: "file",
        creating_job: "job-id",
        data_type: "galaxy.datatypes.data.Text",
        display_apps: [],
        display_types: [],
        download_url: `/api/datasets/${summary.id}/display`,
        drs_id: summary.id,
        file_ext: summary.extension ?? "txt",
        file_size: 0,
        hashes: [],
        hda_ldda: "hda",
        meta_files: [],
        model_class: "HistoryDatasetAssociation",
        permissions: { access: [], manage: [] },
        rerunnable: false,
        resubmitted: false,
        sources: [],
        uuid: "00000000-0000-4000-8000-000000000001",
        validated_state: "unknown",
        ...overrides,
    };
}
