import { computed, onUnmounted, type Ref, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import type { JobConsoleOutput } from "@/api/jobs";
import { useJobStore } from "@/stores/jobStore";
import { rethrowSimple } from "@/utils/simple-error";
import { stateIsTerminal } from "@/utils/utils";

const DEFAULT_POLL_INTERVAL_MS = 3000;

/** Reactively reads (and keeps polling) a job's details via `jobStore`.
 *
 * @param options Has option `full?: boolean` (default `true`) which picks which representation to
 * request:
 *
 * `full = false` only needs the smaller, base job shape, and is satisfied by an already-cached job of
 * either shape.
 * A job already cached as terminal is never re-fetched, regardless of which shape is requested (unless a `full: true`
 * caller needs to upgrade a base-only cached entry).
 */
export function useJobDetails(jobId: Ref<string | undefined>, options: { autoRefresh?: boolean; full?: boolean } = {}) {
    const { autoRefresh = true, full = true } = options;
    const jobStore = useJobStore();

    const job = computed(() => jobStore.getJob(jobId.value ?? "") ?? null);
    const error = computed(() => (jobId.value ? jobStore.getJobLoadError(jobId.value) : null));
    const loading = computed(() => (jobId.value ? jobStore.isLoadingJob(jobId.value) : false));

    watch(
        jobId,
        (id) => {
            if (autoRefresh && id) {
                jobStore.pollJobUntilTerminal({ id, full });
            }
        },
        { immediate: true },
    );

    return { job, error, loading };
}

/** Fetches and auto-polls a job's console output (stdout/stderr)*/
export function useJobConsoleOutput(
    jobId: Ref<string | undefined>,
    options: { autoRefresh?: boolean; pollInterval?: number; chunkLength?: number } = {},
) {
    const { autoRefresh = true, pollInterval = DEFAULT_POLL_INTERVAL_MS, chunkLength = 50000 } = options;

    const stdout = ref("");
    const stderr = ref("");
    const state = ref<string | null | undefined>(undefined);
    const error = ref<unknown>(null);

    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    let currentJobId: string | undefined;

    function clearPoll() {
        if (timeoutId !== null) {
            clearTimeout(timeoutId);
            timeoutId = null;
        }
    }

    async function fetchConsoleOutput(id: string) {
        const { data, error: fetchError } = await GalaxyApi().GET("/api/jobs/{job_id}/console_output", {
            params: {
                path: { job_id: id },
                query: {
                    stdout_position: stdout.value.length,
                    stdout_length: chunkLength,
                    stderr_position: stderr.value.length,
                    stderr_length: chunkLength,
                },
            },
        });
        if (fetchError) {
            rethrowSimple(fetchError);
        }
        return data as JobConsoleOutput;
    }

    async function poll(id: string) {
        try {
            const result = await fetchConsoleOutput(id);
            if (id !== currentJobId) {
                return;
            }
            if (result.stdout != null) {
                stdout.value += result.stdout;
            }
            if (result.stderr != null) {
                stderr.value += result.stderr;
            }
            state.value = result.state;
            error.value = null;
        } catch (e) {
            if (id !== currentJobId) {
                return;
            }
            error.value = e;
        }

        if (id !== currentJobId) {
            return;
        }
        if (autoRefresh && !stateIsTerminal({ state: state.value })) {
            timeoutId = setTimeout(() => poll(id), pollInterval);
        }
    }

    function restart(id: string | undefined) {
        clearPoll();
        currentJobId = id;
        stdout.value = "";
        stderr.value = "";
        state.value = undefined;
        error.value = null;
        if (id) {
            poll(id);
        }
    }

    watch(jobId, (id) => restart(id), { immediate: true });

    onUnmounted(clearPoll);

    return { stdout, stderr, error };
}
