import { formatDuration, intervalToDuration } from "date-fns";

import type { JobBaseModel } from "@/api/jobs";

export function getJobDuration(job: JobBaseModel): string {
    return formatDuration(intervalToDuration({ start: new Date(job.create_time), end: new Date(job.update_time) }));
}
