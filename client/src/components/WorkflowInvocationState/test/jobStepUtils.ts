import type { JobBaseModel } from "@/api/jobs";

import TEST_JOBS_JSON from "./json/jobs.json";

export const TEST_JOBS_BY_STATES = TEST_JOBS_JSON.reduce(
    (acc: Record<string, JobBaseModel[]>, job) => {
        if (!acc[job.state]) {
            acc[job.state] = [];
        }
        acc[job.state]!.push(job as JobBaseModel);
        return acc;
    },
    {} as Record<string, JobBaseModel[]>,
);
