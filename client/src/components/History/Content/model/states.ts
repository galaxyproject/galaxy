import type { DCESummary, HDADetailed, HDCADetailed } from "@/api";
import { ERROR_DATASET_STATES, NON_TERMINAL_DATASET_STATES } from "@/api/datasets";
import type { HistoryContentsResult } from "@/api/histories";
import type { components } from "@/api/schema";

import { DatasetStateSummary } from "../Collection/DatasetStateSummary";

type HistoryContentItem = HistoryContentsResult[number];

function isHDCAItem(item: HistoryContentItem | HDADetailed | HDCADetailed | DCESummary): boolean {
    return (
        item &&
        typeof item === "object" &&
        "history_content_type" in item &&
        item.history_content_type === "dataset_collection"
    );
}

function isDCEWithCollection(item: HistoryContentItem | HDADetailed | HDCADetailed | DCESummary): boolean {
    return item && typeof item === "object" && "collection_type" in item && item.collection_type !== undefined;
}

type DatasetState = components["schemas"]["DatasetState"];
// The 'failed' state is for the collection job state summary, not a dataset state.
export type State =
    | DatasetState
    | "failed"
    | "placeholder"
    | "failed_populated_state"
    | "new_populated_state"
    | "inaccessible";

interface StateRepresentation {
    status: "success" | "warning" | "info" | "danger" | "secondary";
    text?: string;
    displayName?: string;
    icon?: string;
    spin?: boolean;
    nonDb?: boolean;
}

export type StateMap = {
    [__ in State]: StateRepresentation;
};

/**
 * Client representation of state and state messages.
 * See: https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/model/__init__.py#L3292 for a list of available states.
 */
export const STATES: StateMap = {
    /** has successfully completed running */
    ok: {
        status: "success",
        displayName: "ok",
    },
    /** has no data */
    empty: {
        status: "success",
        text: "No data.",
        displayName: "empty",
    },
    /** was created without a tool */
    new: {
        status: "warning",
        text: "This is a new dataset and not all of its data are available yet.",
        displayName: "new",
        icon: "clock",
    },
    /** the job that will produce the dataset queued in the runner */
    queued: {
        status: "warning",
        text: "This job is waiting to run.",
        displayName: "queued",
        icon: "clock",
    },
    /** the job that will produce the dataset is running */
    running: {
        status: "warning",
        text: "This job is currently running.",
        displayName: "running",
        icon: "spinner",
        spin: true,
    },
    /** metadata for the dataset is being discovered/set */
    setting_metadata: {
        status: "warning",
        text: "Metadata is being auto-detected.",
        displayName: "setting metadata",
        icon: "spinner",
        spin: true,
    },
    /** is uploading and not ready */
    upload: {
        status: "warning",
        text: "This dataset is currently uploading.",
        displayName: "uploading",
        icon: "spinner",
        spin: true,
    },
    /** remote dataset */
    deferred: {
        status: "info",
        text: "This dataset is remote, has not been ingested by Galaxy, and full metadata may not be available.",
        displayName: "deferred",
        icon: "cloud",
    },
    /** the job that will produce the dataset paused */
    paused: {
        status: "info",
        text: "This job is paused. Use the 'Resume Paused Jobs' in the history menu to resume.",
        displayName: "paused",
        icon: "pause",
    },
    /** deleted while uploading */
    discarded: {
        status: "danger",
        text: "This dataset is discarded - the job creating it may have been cancelled or it may have been imported without file data.",
        displayName: "discarded",
        icon: "exclamation-triangle",
    },
    /** the tool producing this dataset has errored */
    error: {
        status: "danger",
        text: "An error occurred with this dataset.",
        displayName: "error",
        icon: "exclamation-triangle",
    },
    /** metadata discovery/setting failed or errored (but otherwise ok) */
    failed_metadata: {
        status: "danger",
        text: "Metadata generation failed. Please retry.",
        displayName: "failed metadata",
        icon: "exclamation-triangle",
    },
    /** the job has failed, this is not a dataset but a job state used in the collection job state summary. */
    failed: {
        status: "danger",
        displayName: "failed",
        icon: "exclamation-triangle",
    },
    /** the dataset is not yet loaded in the UI. This state is only visual and transitional, it does not exist in the database. */
    placeholder: {
        status: "secondary",
        text: "This dataset is being fetched.",
        displayName: "loading",
        icon: "spinner",
        spin: true,
        nonDb: true,
    },
    /** the `populated_state: failed`. This state is only visual and transitional, it does not exist in the database. */
    failed_populated_state: {
        status: "danger",
        text: "Failed to populate the collection.",
        displayName: "failed",
        icon: "exclamation-triangle",
        nonDb: true,
    },
    /** the `populated_state: new`. This state is only visual and transitional, it does not exist in the database. */
    new_populated_state: {
        status: "warning",
        text: "This is a new collection and not all of its data are available yet.",
        displayName: "new",
        icon: "clock",
        nonDb: true,
    },
    inaccessible: {
        status: "warning",
        text: "User not allowed to access this dataset.",
        displayName: "inaccessible",
        icon: "lock",
        nonDb: true,
    },
} as const satisfies StateMap;

/** We want to display a single state for a dataset collection whose elements may have mixed states.
 * This list is ordered from highest to lowest priority. If any element is in error state the whole collection should be in error.
 */
export const HIERARCHICAL_COLLECTION_JOB_STATES = [
    "error",
    "failed",
    "upload",
    "paused",
    "running",
    "queued",
    "new",
] as const;

/** Similar hierarchy for dataset states, ordered from highest to lowest priority. */
export const HIERARCHICAL_COLLECTION_DATASET_STATES = [
    ...(ERROR_DATASET_STATES as readonly DatasetState[]),
    ...(NON_TERMINAL_DATASET_STATES as readonly DatasetState[]),
    "deferred" as const,
    "discarded" as const,
] as const satisfies readonly DatasetState[];

export function getContentItemState(item: HistoryContentItem | HDADetailed | HDCADetailed): State {
    if (isHDCAItem(item) || isDCEWithCollection(item)) {
        if ("populated_state" in item && item.populated_state === "failed") {
            return "failed_populated_state";
        }
        if ("populated_state" in item && item.populated_state === "new") {
            return "new_populated_state";
        }

        // Check dataset states first (higher priority for actual data states)
        if ("elements_states" in item && item.elements_states) {
            const datasetSummary = new DatasetStateSummary(
                item as {
                    elements_states?: Record<string, number>;
                    elements_deleted?: number;
                    populated_state?: string | null;
                }
            );
            for (const datasetState of HIERARCHICAL_COLLECTION_DATASET_STATES) {
                if (datasetSummary.get(datasetState) > 0) {
                    return datasetState;
                }
            }
        }

        // Fall back to job states if no dataset states
        if ("job_state_summary" in item && item.job_state_summary) {
            const jobStateSummary = item.job_state_summary as Record<string, number>;
            for (const jobState of HIERARCHICAL_COLLECTION_JOB_STATES) {
                if ((jobStateSummary[jobState] || 0) > 0) {
                    return jobState;
                }
            }
        }
    } else if ("accessible" in item && item.accessible === false) {
        return "inaccessible";
    } else if ("state" in item && item.state) {
        return item.state;
    }
    return "ok";
}
