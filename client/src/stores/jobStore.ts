import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { GalaxyApi } from "@/api";
import { type ResponseVal, type ShowFullJobResponse, TERMINAL_STATES } from "@/api/jobs";
import { useResourceWatcher } from "@/composables/resourceWatcher";
import { isRetryableApiError, MAX_RETRIES, rethrowSimpleWithStatus } from "@/utils/simple-error";

interface JobFetchParams {
    id: string;
    /** Whether to request the full job representation. Defaults to `true`. */
    full?: boolean;
}

interface PollEntry {
    watcher: ReturnType<typeof useResourceWatcher>;
    full: boolean;
    refCount: number;
}

/** Max number of jobs to keep cached at once, to avoid unbounded memory growth over a long
 * session. Exported so tests can exercise eviction. */
export const MAX_CACHED_JOBS = 40;

/**
 * The Job store for managing job data and tool-run responses.
 *
 * - Caches fetched jobs, capped at `MAX_CACHED_JOBS` via LRU (Least Recently Used) eviction.
 *   Once over the cap, the longest-untouched job is dropped first.
 * - Allows both base and full requests for the same job id to be tracked independently, but merges
 *   the full response into the cached job rather than overwriting it entirely.
 * - Polls a job until it reaches a terminal state, deduped so multiple callers watching the same
 *   job share one poll.
 * - Stores the latest tool-run response (used by the post-run "success" view).
 */
export const useJobStore = defineStore("jobStore", () => {
    const latestResponse = ref<ResponseVal | null>(null);

    const storedJobs = ref<{ [id: string]: ShowFullJobResponse }>({});
    const loadingErrors = ref<{ [id: string]: Error }>({});
    const retryCounts: { [id: string]: number } = {};

    /** Keyed by `id:full` so a base and a full request for the same job id are tracked separately.
     * Otherwise whichever one resolved first would be (wrongly) treated as satisfying both.
     */
    const loadingRequests = new Map<string, Promise<ShowFullJobResponse | undefined>>();

    /** Counts in-flight requests per job id (a base and a full request can be in flight for the
     * same id at once, under separate `loadingRequests` keys) so `isLoadingJob` stays true until
     * *all* of them finish, not just whichever happens to resolve first. */
    const loadingCountsByJobId = ref<{ [id: string]: number }>({});

    function saveLatestResponse(newResponse: ResponseVal) {
        latestResponse.value = newResponse;
    }

    /** Keys a request by `id:full` so that base and full **requests** for the same job id are tracked separately. */
    function requestKey(params: JobFetchParams): string {
        return `${params.id}:${params.full ?? true}`;
    }

    /** Whether a failed fetch for `id` is worth retrying: the error is a retryable status and we
     * haven't already retried it `MAX_RETRIES` times. */
    function canRetryJob(id: string): boolean {
        const existingError = loadingErrors.value[id];
        return !!existingError && isRetryableApiError(existingError) && (retryCounts[id] ?? 0) <= MAX_RETRIES;
    }

    const getJobLoadError = computed(() => (id: string) => loadingErrors.value[id] ?? null);

    const isLoadingJob = computed(() => (id: string) => (loadingCountsByJobId.value[id] ?? 0) > 0);

    function mergeJob(freshJob: ShowFullJobResponse, existingJob?: ShowFullJobResponse): ShowFullJobResponse {
        return existingJob ? { ...existingJob, ...freshJob } : freshJob;
    }

    async function fetchJobFromApi(params: JobFetchParams): Promise<ShowFullJobResponse> {
        const { data, error, response } = await GalaxyApi().GET("/api/jobs/{job_id}", {
            params: { path: { job_id: params.id }, query: { full: params.full ?? true } },
        });
        if (error) {
            rethrowSimpleWithStatus(error, response);
        }
        return data;
    }

    /** Fetches a job, deduping concurrent requests for the same id+`full` shape, merging the
     * result into the cache, and tracking loading/retry state. */
    async function fetchAndCacheJob(params: JobFetchParams): Promise<ShowFullJobResponse | undefined> {
        const key = requestKey(params);
        const inFlight = loadingRequests.get(key);
        if (inFlight) {
            return inFlight;
        }

        // Increment the count of in-flight requests for this job id. This ensures that `isLoadingJob`
        // remains true until all concurrent requests for the same job id (base and full) have completed.
        loadingCountsByJobId.value[params.id] = (loadingCountsByJobId.value[params.id] ?? 0) + 1;

        const fetchPromise = (async () => {
            try {
                const freshJob = await fetchJobFromApi(params);
                const job = mergeJob(freshJob, storedJobs.value[params.id]);
                storedJobs.value[params.id] = job;
                delete loadingErrors.value[params.id];
                delete retryCounts[params.id];
                return job;
            } catch (error) {
                retryCounts[params.id] = (retryCounts[params.id] ?? 0) + 1;
                loadingErrors.value[params.id] = error as Error;
                return undefined;
            } finally {
                loadingRequests.delete(key);
                const remaining = (loadingCountsByJobId.value[params.id] ?? 1) - 1;
                if (remaining <= 0) {
                    delete loadingCountsByJobId.value[params.id];
                } else {
                    loadingCountsByJobId.value[params.id] = remaining;
                }
            }
        })();

        loadingRequests.set(key, fetchPromise);
        return fetchPromise;
    }

    function removeJob(id: string) {
        delete storedJobs.value[id];
        delete loadingErrors.value[id];
        delete retryCounts[id];
    }

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

    /** An overloaded fetch function that ensures the job is retrieved from the cache, but with the
     * additional, optional `full` option for requesting the full job representation. */
    async function fetchJob(params: JobFetchParams) {
        markUsed(params.id);
        const job = await fetchAndCacheJob(params);
        evictIfOverCap();
        return job;
    }

    const getJob = computed(() => (id: string) => {
        const job = storedJobs.value[id] ?? null;
        if (job) {
            // Getting a cached job also marks it recently-used. Otherwise a job that's displayed
            // but never re-fetched (already terminal) could get evicted while still on screen.
            markUsed(id);
        } else if (id && !loadingRequests.has(requestKey({ id })) && !getJobLoadError.value(id)) {
            // Auto-fetch on read, same as the old `useKeyedCache`-backed `getJob`: a reader that
            // never calls `pollJobUntilTerminal` (e.g. wants a one-off, non-polled lookup) still
            // gets the job fetched the first time it's read.
            fetchJob({ id });
        }
        return job;
    });

    /** Tracks job ids for which the full representation has been loaded. */
    const fullyLoadedJobIds = new Set<string>();

    /** A track of all active polls (by `job_id` and whether the stored representation is full),
     * plus a count of how many callers still want that poll running, so we don't duplicate polls
     * for the same ID and stop polling once the last interested caller goes away. */
    const activePolls = new Map<string, PollEntry>();

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
            return { stopWatchingJob: () => stopWatchingJob(id, runningPoll) };
        }

        const watcher = useResourceWatcher(
            async () => {
                // Read (not close over) the current requested level as a later call may have
                // upgraded this poll to `full: true` since it started.
                const requestFull = activePolls.get(id)?.full ?? full;
                let job = await fetchJob({ id, full: requestFull });
                if (job && requestFull) {
                    fullyLoadedJobIds.add(id);
                }
                if (job && TERMINAL_STATES.indexOf(job.state) !== -1) {
                    // The poll may have been upgraded to `full` *after* the fetch above was
                    // already made with the pre-upgrade value, in which case a terminal result
                    // here would otherwise stop polling having only ever fetched the base
                    // representation. Fetch full once more before disposing so the upgrade is
                    // still honored.
                    if (activePolls.get(id)?.full && !fullyLoadedJobIds.has(id)) {
                        job = await fetchJob({ id, full: true });
                        if (job) {
                            fullyLoadedJobIds.add(id);
                        }
                    }
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
        const pollEntry = { watcher, full, refCount: 1 };
        activePolls.set(id, pollEntry);
        watcher.startWatchingResource();
        return { stopWatchingJob: () => stopWatchingJob(id, pollEntry) };
    }

    /** One caller is done watching a job; the poll stops once refCount hits 0.
     *
     * `entry` is the specific poll entry this caller's handle was issued for.
     * If `id`'s current entry in `activePolls` is a *different* one (the original poll already ended
     * and a new one started for the same id since), this is a stale handle and must be a no-op:
     * decrementing the new, unrelated poll's `refCount` could stop it while a still-active caller
     * still needs it.
     */
    function stopWatchingJob(id: string, entry: PollEntry) {
        const runningPoll = activePolls.get(id);
        if (!runningPoll || runningPoll !== entry) {
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
        getJob,
        getJobLoadError,
        isLoadingJob,
        latestResponse,
        pollJobUntilTerminal,
    };
});
