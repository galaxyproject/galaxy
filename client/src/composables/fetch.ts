import { computed, ref, watch } from "vue";

import { ERROR_STATES, TERMINAL_STATES } from "@/api/jobs";
import { fetch, type FetchDataPayload, fetchJobErrorMessage } from "@/api/tools";
import { useJobStore } from "@/stores/jobStore";
import { errorMessageAsString } from "@/utils/simple-error";

export function useFetchJobMonitor() {
    const fetchJobId = ref<string | undefined>(undefined);
    const { getJob, pollJobUntilTerminal } = useJobStore();

    const fetchComplete = ref(false);
    const fetchError = ref<string | undefined>(undefined);
    const waitingOnFetch = ref(false);

    const job = computed(() => {
        if (fetchJobId.value) {
            const jobId = fetchJobId.value;
            const job = getJob(jobId);
            if (job) {
                return job;
            }
        }
        return undefined;
    });

    async function fetchAndWatch(payload: FetchDataPayload) {
        try {
            waitingOnFetch.value = true;
            const jobId = await fetch(payload);
            fetchJobId.value = jobId;
            // we monitor the job with the watch below and update the state when needed.
            pollJobUntilTerminal({ id: jobId });
        } catch (e) {
            fetchError.value = `Error importing data: ${errorMessageAsString(e)}`;
            waitingOnFetch.value = false;
        }
    }

    watch(job, (newValue) => {
        const state = newValue?.state ?? "new";
        if (TERMINAL_STATES.indexOf(state) !== -1) {
            if (ERROR_STATES.indexOf(state) !== -1) {
                fetchError.value = fetchJobErrorMessage(newValue!);
            } else {
                fetchComplete.value = true;
            }
            waitingOnFetch.value = false;
        }
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
