import type { components } from "@/api";
import { http } from "@/api/client/__mocks__/http";

type JobState = components["schemas"]["JobState"];

/** The history being exported. */
export const EXPORTED_HISTORY_ID = "5f1915bcf9745345";

/** The job that writes the history's archive. */
export const EXPORT_JOB_ID = "8c49be448cfe29bc";

/** The export job as `/api/jobs/{job_id}?full=true` shows it, in `state`. */
export function exportJob(state: JobState): components["schemas"]["ShowFullJobResponse"] {
    return {
        model_class: "Job",
        id: EXPORT_JOB_ID,
        tool_id: "__EXPORT_HISTORY__",
        history_id: EXPORTED_HISTORY_ID,
        state,
        create_time: "2026-10-01T12:00:00",
        update_time: "2026-10-01T12:00:05",
        exit_code: state === "ok" ? 0 : null,
        inputs: {},
        outputs: {},
        output_collections: {},
        params: {},
    };
}

/** Answers the export job's polls with the state `stateNow()` returns at each request. */
export function exportJobHandler(stateNow: () => JobState) {
    return http.get("/api/jobs/{job_id}", ({ params, response }) =>
        response(200).json({ ...exportJob(stateNow()), id: params.job_id }),
    );
}
