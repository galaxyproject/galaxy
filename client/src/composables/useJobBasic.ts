import { computed, type Ref } from "vue";

import { useJobStore } from "@/stores/jobStore";

/**
 * Reactive accessor for a single job's details — shares the jobStore's keyed
 * cache so multiple consumers with the same id don't refetch. Returns null
 * when the id is empty or the job hasn't loaded yet.
 */
export function useJobBasic(jobId: Ref<string | null | undefined>) {
    const jobStore = useJobStore();
    const job = computed(() => (jobId.value ? (jobStore.getJob(jobId.value) ?? null) : null));
    return { job };
}
