import { computed, onUnmounted, type Ref, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import type { JobConsoleOutput } from "@/api/jobs";
import { useResourceWatcher } from "@/composables/resourceWatcher";
import { useJobStore } from "@/stores/jobStore";
import { rethrowSimple } from "@/utils/simple-error";
import { stateIsTerminal } from "@/utils/utils";

const DEFAULT_POLL_INTERVAL_MS = 3000;

/** Reads a retained job and polls it until completion. Set `poll: false` for a single fetch. */
export function useJobDetails(jobId: Ref<string | undefined>, options: { full?: boolean; poll?: boolean } = {}) {
    const { full = true, poll = true } = options;
    const jobStore = useJobStore();

    const job = computed(() => (jobId.value ? jobStore.getCachedJob(jobId.value) : null));
    const error = computed(() => (jobId.value ? jobStore.getJobLoadError(jobId.value) : null));
    const loading = computed(() => (jobId.value ? jobStore.isLoadingJob(jobId.value) : false));

    watch(
        jobId,
        (id, _oldId, onCleanup) => {
            if (!id) {
                return;
            }
            const releaseJob = jobStore.retainJob(id);
            const subscription = poll ? jobStore.pollJobUntilTerminal({ id, full }) : undefined;
            if (!poll) {
                jobStore.fetchJob({ id, full });
            }
            onCleanup(() => {
                subscription?.stopWatchingJob();
                releaseJob?.();
            });
        },
        { immediate: true },
    );

    return { job, error, loading };
}

/** Fetches and auto-polls a job's console output (stdout/stderr)*/
export function useJobConsoleOutput(
    jobId: Ref<string | undefined>,
    options: { pollInterval?: number; chunkLength?: number } = {},
) {
    const { pollInterval = DEFAULT_POLL_INTERVAL_MS, chunkLength = 50000 } = options;

    const stdout = ref("");
    const stderr = ref("");
    const state = ref<string | null | undefined>(undefined);
    const error = ref<unknown>(null);

    let currentJobId: string | undefined;
    /**
     * Incremented on every `restart()` call. A response belongs to the current restart only if
     * this still matches the value captured when its fetch began; comparing `id` alone isn't
     * enough, since switching away from a job and back to it reuses the same id for a new restart.
     */
    let restartCount = 0;

    async function fetchConsoleOutput(id: string) {
        const {
            data,
            error: fetchError,
            response,
        } = await GalaxyApi().GET("/api/jobs/{job_id}/console_output", {
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
            // Destinations without live output reporting cannot satisfy subsequent polls either.
            if (response.status === 403 && fetchError.err_code === 403004) {
                return null;
            }
            rethrowSimple(fetchError);
        }
        return data as JobConsoleOutput;
    }

    const watcher = useResourceWatcher<string>(
        async (id?: unknown) => {
            const fetchRestartCount = restartCount;
            if (typeof id !== "string" || id !== currentJobId) {
                return;
            }
            try {
                const result = await fetchConsoleOutput(id);
                if (fetchRestartCount !== restartCount) {
                    return;
                }
                if (result === null) {
                    error.value = null;
                    watcher.stopWatchingResource();
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
                if (stateIsTerminal({ state: state.value })) {
                    watcher.stopWatchingResource();
                }
            } catch (e) {
                if (fetchRestartCount !== restartCount) {
                    return;
                }
                error.value = e;
            }
        },
        { shortPollingInterval: pollInterval, longPollingInterval: pollInterval },
    );

    function restart(id: string | undefined) {
        watcher.stopWatchingResource();
        restartCount++;
        currentJobId = id;
        stdout.value = "";
        stderr.value = "";
        state.value = undefined;
        error.value = null;
        if (id) {
            watcher.startWatchingResource(id);
        }
    }

    watch(jobId, (id) => restart(id), { immediate: true });

    onUnmounted(() => watcher.dispose());

    return { stdout, stderr, error };
}
