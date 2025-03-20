import { isHDCA } from "@/api";
import { type components } from "@/api/schema";

type DatasetState = components["schemas"]["DatasetState"];
// The 'failed' state is for the collection job state summary, not a dataset state.
type State =
    | DatasetState
    | "failed"
    | "placeholder"
    | "failed_populated_state"
    | "new_populated_state"
    | "inaccessible";

interface StateRepresentation {
    status: "success" | "warning" | "info" | "danger" | "secondary";
    text?: string;
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
    },
    /** has no data */
    empty: {
        status: "success",
        text: "No data.",
    },
    /** was created without a tool */
    new: {
        status: "warning",
        text: "This is a new dataset and not all of its data are available yet.",
        icon: "clock",
    },
    /** the job that will produce the dataset queued in the runner */
    queued: {
        status: "warning",
        text: "This job is waiting to run.",
        icon: "clock",
    },
    /** the job that will produce the dataset is running */
    running: {
        status: "warning",
        text: "This job is currently running.",
        icon: "spinner",
        spin: true,
    },
    /** metadata for the dataset is being discovered/set */
    setting_metadata: {
        status: "warning",
        text: "Metadata is being auto-detected.",
        icon: "spinner",
        spin: true,
    },
    /** is uploading and not ready */
    upload: {
        status: "warning",
        text: "This dataset is currently uploading.",
        icon: "spinner",
        spin: true,
    },
    /** remote dataset */
    deferred: {
        status: "info",
        text: "This dataset is remote, has not been ingested by Galaxy, and full metadata may not be available.",
        icon: "cloud",
    },
    /** the job that will produce the dataset paused */
    paused: {
        status: "info",
        text: "This job is paused. Use the 'Resume Paused Jobs' in the history menu to resume.",
        icon: "pause",
    },
    /** deleted while uploading */
    discarded: {
        status: "danger",
        text: "This dataset is discarded - the job creating it may have been cancelled or it may have been imported without file data.",
        icon: "exclamation-triangle",
    },
    /** the tool producing this dataset has errored */
    error: {
        status: "danger",
        text: "An error occurred with this dataset:",
        icon: "exclamation-triangle",
    },
    /** metadata discovery/setting failed or errored (but otherwise ok) */
    failed_metadata: {
        status: "danger",
        text: "Metadata generation failed. Please retry.",
        icon: "exclamation-triangle",
    },
    /** the job has failed, this is not a dataset but a job state used in the collection job state summary. */
    failed: {
        status: "danger",
        icon: "exclamation-triangle",
    },
    /** the dataset is not yet loaded in the UI. This state is only visual and transitional, it does not exist in the database. */
    placeholder: {
        status: "secondary",
        text: "This dataset is being fetched.",
        icon: "spinner",
        spin: true,
        nonDb: true,
    },
    /** the `populated_state: failed`. This state is only visual and transitional, it does not exist in the database. */
    failed_populated_state: {
        status: "danger",
        text: "Failed to populate the collection.",
        icon: "exclamation-triangle",
        nonDb: true,
    },
    /** the `populated_state: new`. This state is only visual and transitional, it does not exist in the database. */
    new_populated_state: {
        status: "warning",
        text: "This is a new collection and not all of its data are available yet.",
        icon: "clock",
        nonDb: true,
    },
    inaccessible: {
        status: "warning",
        text: "User not allowed to access this dataset.",
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

export function getContentItemState(item: any) {
    if (isHDCA(item)) {
        if (item.populated_state === "failed") {
            return "failed_populated_state";
        }
        if (item.populated_state === "new") {
            return "new_populated_state";
        }
        if (item.job_state_summary) {
            for (const jobState of HIERARCHICAL_COLLECTION_JOB_STATES) {
                if (item.job_state_summary[jobState] > 0) {
                    return jobState;
                }
            }
        }
    } else if (item.accessible === false) {
        return "inaccessible";
    } else if (item.state) {
        return item.state;
    }
    return "ok";
}
