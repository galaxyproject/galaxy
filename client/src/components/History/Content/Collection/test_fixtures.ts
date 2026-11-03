import type { components } from "@/api";

import { JobStateSummary } from "./JobStateSummary";

type HDCJobStateSummary = components["schemas"]["HDCJobStateSummary"];

const NO_JOBS: HDCJobStateSummary = {
    all_jobs: 0,
    deleted: 0,
    deleted_new: 0,
    error: 0,
    failed: 0,
    new: 0,
    ok: 0,
    paused: 0,
    queued: 0,
    resubmitted: 0,
    running: 0,
    skipped: 0,
    upload: 0,
    waiting: 0,
};

/** A populated collection's job state summary with the given job counts; Galaxy sends every other state as 0. */
export function jobStateSummary(jobCounts: Partial<HDCJobStateSummary>) {
    return new JobStateSummary({ job_state_summary: { ...NO_JOBS, ...jobCounts }, populated_state: "ok" });
}
