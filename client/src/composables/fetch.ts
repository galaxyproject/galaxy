import { computed, type Ref, ref, watch } from "vue";

import { ERROR_STATES, TERMINAL_STATES } from "@/api/jobs";
import { fetch, type FetchDataPayload, fetchJobErrorMessage } from "@/api/tools";
import { useResourceWatcher } from "@/composables/resourceWatcher";
import { useJobStore } from "@/stores/jobStore";
import { errorMessageAsString } from "@/utils/simple-error";

export function useJobWatcher(jobId: Ref<string | undefined>) {
    const { fetchJob, getJob } = useJobStore();
    const jobRequestError = ref<string | undefined>(undefined);

    async function jobResourceHandler() {
        if (!jobId.value) {
            return;
        }
        jobRequestError.value = undefined;
        try {
            await fetchJob({ id: jobId.value! });
        } catch (error) {
            jobRequestError.value = `Error requesting job: ${errorMessageAsString(error)}`;
        }
    }

    const job = computed(() => {
        if (jobId.value) {
            const jobIdVal = jobId.value;
            const job = getJob(jobIdVal);
            if (job) {
                return job;
            }
        }
        return undefined;
    });

    const { startWatchingResourceIfNeeded, stopWatchingResourceIfNeeded } = useResourceWatcher(jobResourceHandler);

    watch(
        job,
        (job) => {
            if (job) {
                const newJobState = job.state;
                const isTerminal = TERMINAL_STATES.indexOf(newJobState) !== -1;
                if (isTerminal) {
                    stopWatchingResourceIfNeeded();
                }
            } else {
                startWatchingResourceIfNeeded();
            }
        },
        {
            immediate: true,
        }
    );

    return {
        job,
        jobRequestError,
    };
}

export function useFetchJobMonitor() {
    const fetchJobId = ref<string | undefined>(undefined);

    const { job, jobRequestError } = useJobWatcher(fetchJobId);

    const fetchComplete = ref(false);
    const fetchRequestError = ref<string | undefined>(undefined);
    const jobFailedError = ref<string | undefined>(undefined);
    const waitingOnFetch = ref(false);

    async function fetchAndWatch(payload: FetchDataPayload) {
        waitingOnFetch.value = true;
        try {
            const jobId = await fetch(payload);
            fetchJobId.value = jobId;
        } catch (e) {
            fetchRequestError.value = `Error importing data: ${errorMessageAsString(e)}`;
            waitingOnFetch.value = false;
        }
    }

    watch(job, (newValue) => {
        const state = newValue?.state ?? "new";
        if (TERMINAL_STATES.indexOf(state) !== -1) {
            if (ERROR_STATES.indexOf(state) !== -1) {
                jobFailedError.value = fetchJobErrorMessage(newValue!);
            } else {
                fetchComplete.value = true;
            }
            waitingOnFetch.value = false;
        }
    });

    const fetchError = computed(() => {
        return fetchRequestError.value || jobRequestError.value || jobFailedError.value;
    });

    return {
        fetchJobId,
        fetchAndWatch,
        fetchComplete,
        fetchError,
        job,
        waitingOnFetch,
    };
}
