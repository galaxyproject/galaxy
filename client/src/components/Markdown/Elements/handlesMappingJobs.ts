import { format, parseISO } from "date-fns";
import { computed, type Ref, ref, watch } from "vue";

import { fetcher } from "@/api/schema";

const jobsFetcher = fetcher.path("/api/jobs").method("get").create();

export interface SelectOption {
    value: string;
    text: string;
}

interface Job {
    id: string;
    create_time: string;
}

export function useMappingJobs(
    singleJobId: Ref<string | undefined>,
    implicitCollectionJobsId: Ref<string | undefined>
) {
    const selectJobOptions = ref<SelectOption[]>([]);
    const selectedJob = ref<string | undefined>(undefined);
    const targetJobId = computed<string | undefined>(() => {
        if (singleJobId.value) {
            return singleJobId.value;
        } else {
            return selectedJob.value;
        }
    });
    watch(
        implicitCollectionJobsId,
        async () => {
            if (implicitCollectionJobsId.value) {
                const response = await jobsFetcher({ implicit_collection_jobs_id: implicitCollectionJobsId.value });
                const jobs: Job[] = response.data as unknown as Job[];
                selectJobOptions.value = jobs.map((value, index) => {
                    const isoCreateTime = parseISO(`${value.create_time}Z`);
                    const prettyTime = format(isoCreateTime, "eeee MMM do H:mm:ss yyyy zz");
                    return { value: value.id, text: `${index + 1}: ${prettyTime}` };
                });
                if (jobs[0]) {
                    const job: Job = jobs[0];
                    selectedJob.value = job.id;
                }
            }
        },
        { immediate: true }
    );
    return { selectJobOptions, selectedJob, targetJobId };
}
