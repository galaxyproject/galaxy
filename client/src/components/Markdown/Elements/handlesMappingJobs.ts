import { format, parseISO } from "date-fns";
import { computed, type Ref, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import { rethrowSimple } from "@/utils/simple-error";

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
                const { data: jobs, error } = await GalaxyApi().GET("/api/jobs", {
                    params: {
                        query: {
                            implicit_collection_jobs_id: implicitCollectionJobsId.value,
                        },
                    },
                });

                if (error) {
                    rethrowSimple(error);
                }

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
