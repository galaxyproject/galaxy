import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { GalaxyApi } from "@/api";
import { type ResponseVal, type ShowFullJobResponse, TERMINAL_STATES } from "@/api/jobs";
import { type FetchParams, useKeyedCache } from "@/composables/keyedCache";
import { useResourceWatcher } from "@/composables/resourceWatcher";
import { rethrowSimpleWithStatus } from "@/utils/simple-error";

interface JobFetchParams extends FetchParams {
    /** Whether to request the full job representation. Defaults to `true`. */
    full?: boolean;
}

/** Max number of jobs to keep cached at once, to avoid unbounded memory growth over a long
 * session. Exported so tests can exercise eviction. */
export const MAX_CACHED_JOBS = 40;

/**
 * The Job store for managing job data and tool-run responses.
 *
 * - Caches fetched jobs, capped at `MAX_CACHED_JOBS` via LRU (Least Recently Used) eviction.
 *   Once over the cap, the longest-untouched job is dropped first.
 * - Polls a job until it reaches a terminal state, deduped so multiple callers watching the same
 *   job share one poll.
 * - Stores the latest tool-run response (used by the post-run "success" view).
 */
export const useJobStore = defineStore("jobStore", () => {
    const latestResponse = ref<ResponseVal | null>(null);

    async function fetchJobById(params: JobFetchParams): Promise<ShowFullJobResponse> {
        const { data, error, response } = await GalaxyApi().GET("/api/jobs/{job_id}", {
            params: { path: { job_id: params.id }, query: { full: params.full ?? true } },
        });
        if (error) {
            rethrowSimpleWithStatus(error, response);
        }
        return data;
    }

    function saveLatestResponse(newResponse: ResponseVal) {
        latestResponse.value = newResponse;
    }

    const {
        storedItems: storedJobs,
        fetchItemById: fetchJobKeyedCache,
        getItemById: getJob,
        getItemLoadError: getJobLoadError,
        isLoadingItem: isLoadingJob,
        removeItemById: removeJob,
        canRetry: canRetryJob,
    } = useKeyedCache<ShowFullJobResponse>(fetchJobById);

    // LRU tracking for `MAX_CACHED_JOBS`: a Map's keys iterate oldest-to-newest, and re-`set`ting
    // a key moves it to the end, so this alone tracks recency order without extra bookkeeping.
    const lruOrder = new Map<string, true>();

    function markUsed(id: string) {
        lruOrder.delete(id);
        lruOrder.set(id, true);
    }

    /** Evicts the oldest cached jobs (skipping any still being polled) until under the cap. */
    function evictIfOverCap() {
        for (const id of lruOrder.keys()) {
            if (lruOrder.size <= MAX_CACHED_JOBS) {
                break;
            }
            if (activePolls.has(id)) {
                continue;
            }
            lruOrder.delete(id);
            removeJob(id);
            fullyLoadedJobIds.delete(id);
        }
    }

    /** An overloaded fetch function that ensures the job is retrieved from the keyed cache,
     * but with the additional, optional `full` option for requesting the full job representation.
     */
    async function fetchJob(params: JobFetchParams) {
        markUsed(params.id);
        const job = await fetchJobKeyedCache(params as FetchParams);
        evictIfOverCap();
        return job;
    }

    // Wraps `getJob` so reading a cached job also marks it recently-used, not just fetching one --
    // otherwise a job that's displayed but never re-fetched (already terminal) could get evicted
    // while still on screen.
    //
    // Kept as a `computed`, matching what `useKeyedCache`'s own `getItemById` returns, so Pinia's
    // testing plugin still treats it as a getter rather than stubbing it like an action.
    const getJobAndMarkUsed = computed(() => (id: string) => {
        const job = getJob.value(id);
        if (job) {
            markUsed(id);
        }
        return job;
    });

    /** Tracks job ids for which the full representation has been loaded. */
    const fullyLoadedJobIds = new Set<string>();

    /** A track of all active polls (by `job_id` and whether the stored representation is full),
     * plus a count of how many callers still want that poll running, so we don't duplicate polls
     * for the same ID and stop polling once the last interested caller goes away. */
    const activePolls = new Map<
        string,
        { watcher: ReturnType<typeof useResourceWatcher>; full: boolean; refCount: number }
    >();

    /**
     * Polls a job until it reaches a terminal state. If the job is already terminal and cached,
     * it may not poll at all. If the stored job is not a full representation and a full one is
     * requested, it will fetch the full representation once *or* switch an ongoing poll to request
     * the full representation if needed.
     *
     * Returns a `stopWatchingJob` function the caller must invoke (e.g. from `onUnmounted`) once it
     * no longer needs this job polled because the underlying poll only actually stops once every caller
     * that started it has done so.
     */
    function pollJobUntilTerminal(params: JobFetchParams): { stopWatchingJob: () => void } {
        const { id, full = true } = params;
        const stopWatchingReturn = { stopWatchingJob: () => {} };

        // Not using `getJob` here because that would trigger a fetch if the job isn't already cached
        const cachedJob = storedJobs.value[id];
        const cachedJobIsTerminal = !!cachedJob && TERMINAL_STATES.indexOf(cachedJob.state) !== -1;

        /** Whether the cached job satisfies the current request, considering the `full` option. */
        const cacheSatisfiesRequest = full ? fullyLoadedJobIds.has(id) : !!cachedJob;
        if (cachedJobIsTerminal && cacheSatisfiesRequest) {
            // Already have everything this call needs, and the job won't change anymore.
            return stopWatchingReturn;
        }

        // The cached job is terminal but doesn't satisfy the currently requested structure
        if (cachedJobIsTerminal) {
            fetchJob({ id, full: true }).then((job) => {
                if (job) {
                    fullyLoadedJobIds.add(id);
                }
            });
            return stopWatchingReturn;
        }

        const runningPoll = activePolls.get(id);
        if (runningPoll !== undefined) {
            runningPoll.refCount++;
            // We need to switch an ongoing non-`full` poll to request `full`.
            if (full && !runningPoll.full) {
                runningPoll.full = true;
            }
            return { stopWatchingJob: () => stopWatchingJob(id) };
        }

        const watcher = useResourceWatcher(
            async () => {
                // Read (not close over) the current requested level as a later call may have
                // upgraded this poll to `full: true` since it started.
                const requestFull = activePolls.get(id)?.full ?? full;
                const job = await fetchJob({ id, full: requestFull });
                if (job && requestFull) {
                    fullyLoadedJobIds.add(id);
                }
                if (job && TERMINAL_STATES.indexOf(job.state) !== -1) {
                    // Terminal jobs never poll again; dispose (not just stop) to release the
                    // watcher's listener, since a new watcher is made if this job is polled again.
                    watcher.dispose();
                    activePolls.delete(id);
                    return;
                }
                if (!job && getJobLoadError.value(id) && !canRetryJob(id)) {
                    // Stop fetching if the fetch failed with a non-retryable error
                    watcher.dispose();
                    activePolls.delete(id);
                }
            },
            { shortPollingInterval: 1000, longPollingInterval: 1000 },
        );
        activePolls.set(id, { watcher, full, refCount: 1 });
        watcher.startWatchingResource();
        return { stopWatchingJob: () => stopWatchingJob(id) };
    }

    /** One caller is done watching a job; the poll stops once refCount hits 0. */
    function stopWatchingJob(id: string) {
        const runningPoll = activePolls.get(id);
        if (!runningPoll) {
            return;
        }
        runningPoll.refCount--;
        if (runningPoll.refCount <= 0) {
            runningPoll.watcher.dispose();
            activePolls.delete(id);
        }
    }

    return {
        fetchJob,
        saveLatestResponse,
        getJob: getJobAndMarkUsed,
        getJobLoadError,
        isLoadingJob,
        latestResponse,
        pollJobUntilTerminal,
    };
});
