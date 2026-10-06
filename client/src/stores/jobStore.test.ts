import { advanceTimersAndFlush } from "@tests/vitest/helpers";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { JobState, ShowFullJobResponse } from "@/api/jobs";

import { MAX_CACHED_JOBS, useJobStore } from "./jobStore";

const { server, http } = useServerMock();

// Cache eviction exercises many requests; API rate limiting has its own tests.
vi.mock("@/api/client/rateLimiter", () => ({ createRateLimiterMiddleware: () => ({ onRequest() {} }) }));

vi.useFakeTimers();

function buildJob(id: string, state: JobState): ShowFullJobResponse {
    return {
        id,
        state,
        model_class: "Job",
        create_time: "2024-01-01T00:00:00",
        update_time: "2024-01-01T00:00:00",
        inputs: {},
        outputs: {},
        output_collections: {},
        params: {},
        tool_id: "cat1",
    } as ShowFullJobResponse;
}

/** Starts `pollJobUntilTerminal` for each id one at a time, awaiting an MSW flush after each. */
async function pollManyJobs(store: ReturnType<typeof useJobStore>, ids: string[]) {
    for (const id of ids) {
        store.pollJobUntilTerminal({ id });
        await flushPromises();
    }
}

describe("useJobStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    afterEach(() => {
        vi.clearAllTimers();
    });

    it("auto-fetches a job on read via getJob, without going through pollJobUntilTerminal", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                callCount++;
                return response(200).json(buildJob("job0", "ok"));
            }),
        );

        const store = useJobStore();
        // Nothing has polled this id -- a plain read should still trigger a fetch, e.g. for a
        // one-off, non-polled lookup that never calls pollJobUntilTerminal.
        expect(store.getJob("job0")).toBeNull();
        await flushPromises();
        expect(callCount).toBe(1);
        expect(store.getJob("job0")?.id).toBe("job0");

        // Reading again is satisfied by the cache, not re-fetched.
        await flushPromises();
        expect(callCount).toBe(1);
    });

    it("does not start a second polling loop for a job id that is already being polled", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                callCount++;
                return response(200).json(buildJob("job1", "running"));
            }),
        );

        const store = useJobStore();
        store.pollJobUntilTerminal({ id: "job1" });
        store.pollJobUntilTerminal({ id: "job1" }); // second caller for the same id
        await flushPromises();

        expect(callCount).toBe(1);

        await advanceTimersAndFlush(1000);
        // Only one loop ticking: one more fetch, not two.
        expect(callCount).toBe(2);
    });

    it("a stale stopWatchingJob handle from an ended poll does not stop a newer poll for the same id", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                callCount++;
                return response(200).json(buildJob("job9", "running"));
            }),
        );

        const store = useJobStore();

        // Consumer A starts a poll and later stops it; this ends the *first* poll entry for
        // "job9" (refCount drops to 0, entry removed from `activePolls`).
        const a = store.pollJobUntilTerminal({ id: "job9" });
        await flushPromises();
        expect(callCount).toBe(1);
        a.stopWatchingJob();

        // Consumer B starts a brand new poll for the same id: a *second*, independent entry.
        const b = store.pollJobUntilTerminal({ id: "job9" });
        await flushPromises();
        expect(callCount).toBe(2);

        // A's handle is invoked again here (e.g. a component unmounting late, calling its cleanup
        // a second time, or having queued the call before A originally stopped). If `activePolls`
        // were keyed only by id, this would decrement *B's* entry (the only one now at "job9") and
        // could stop it even though B still needs it.
        a.stopWatchingJob();

        // B's poll must still be running: we keep fetching.
        await advanceTimersAndFlush(1000);
        expect(callCount).toBe(3);

        b.stopWatchingJob();
        await advanceTimersAndFlush(1000);
        // Now that B has actually released it, the poll really does stop.
        expect(callCount).toBe(3);
    });

    it("stops polling once the job reaches a terminal state", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                callCount++;
                return response(200).json(buildJob("job1", "ok"));
            }),
        );

        const store = useJobStore();
        store.pollJobUntilTerminal({ id: "job1" });
        await flushPromises();
        expect(callCount).toBe(1);

        await advanceTimersAndFlush(5000);
        expect(callCount).toBe(1);
    });

    it("does not re-fetch a job that is already cached in a terminal state", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                callCount++;
                return response(200).json(buildJob("job1", "ok"));
            }),
        );

        const store = useJobStore();
        store.pollJobUntilTerminal({ id: "job1" });
        await flushPromises();
        expect(callCount).toBe(1);

        // Let the loop's next tick see the terminal state and clean itself up.
        await advanceTimersAndFlush(1000);
        expect(callCount).toBe(1); // still terminal, no second fetch from that loop

        // Calling again for the same (now terminal, cached) id must not trigger a new fetch --
        // real job ids never go non-terminal again, so the cache can be trusted permanently.
        store.pollJobUntilTerminal({ id: "job1" });
        await flushPromises();
        expect(callCount).toBe(1);
    });

    it("skips the initial fetch entirely when the job is already cached and terminal", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                callCount++;
                return response(200).json(buildJob("job2", "ok"));
            }),
        );

        const store = useJobStore();
        store.pollJobUntilTerminal({ id: "job2" });
        await flushPromises();
        expect(callCount).toBe(1);

        // A brand new call for the same id, from a totally separate caller, should be satisfied
        // by the cache without issuing any request at all.
        store.pollJobUntilTerminal({ id: "job2" });
        await flushPromises();
        expect(callCount).toBe(1);
    });

    it("upgrades a base-only cached job to full when a full: true caller asks for it", async () => {
        let callCount = 0;
        let lastFullParam: string | null = null;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response, request }) => {
                callCount++;
                lastFullParam = new URL(request.url).searchParams.get("full");
                return response(200).json(buildJob("job3", "ok"));
            }),
        );

        const store = useJobStore();
        store.pollJobUntilTerminal({ id: "job3", full: false });
        await flushPromises();
        expect(callCount).toBe(1);
        expect(lastFullParam).toBe("false");

        // A full: true caller for the same (terminal, base-only cached) id must still fetch --
        // the cache doesn't yet hold the full shape.
        store.pollJobUntilTerminal({ id: "job3", full: true });
        await flushPromises();
        expect(callCount).toBe(2);
        expect(lastFullParam).toBe("true");

        // Once upgraded, a later full: false caller is satisfied by the now-full cache.
        store.pollJobUntilTerminal({ id: "job3", full: false });
        await flushPromises();
        expect(callCount).toBe(2);
    });

    it("does not re-fetch a terminal job that was already cached full via getJob, not pollJobUntilTerminal", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                callCount++;
                return response(200).json(buildJob("job10", "ok"));
            }),
        );

        const store = useJobStore();
        // Cached via getJob's auto-fetch (default full: true), not via pollJobUntilTerminal.
        // Nothing marks this id as "fully loaded" unless every fetch path does so consistently.
        store.getJob("job10");
        await flushPromises();
        expect(callCount).toBe(1);

        // A later poll (default full: true) for the same id must be satisfied by the cache.
        store.pollJobUntilTerminal({ id: "job10" });
        await flushPromises();
        expect(callCount).toBe(1);
    });

    it("does not skip a non-terminal job even if a base version is already cached", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                callCount++;
                return response(200).json(buildJob("job4", "running"));
            }),
        );

        const store = useJobStore();
        store.pollJobUntilTerminal({ id: "job4", full: false });
        await flushPromises();
        expect(callCount).toBe(1);

        // Still running -- a second caller must keep the poll going, not treat the cache as final.
        await advanceTimersAndFlush(1000);
        expect(callCount).toBe(2);
    });

    it("upgrades an already-running poll for a non-terminal job to full on its next tick", async () => {
        let callCount = 0;
        let lastFullParam: string | null = null;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response, request }) => {
                callCount++;
                lastFullParam = new URL(request.url).searchParams.get("full");
                return response(200).json(buildJob("job5", "running"));
            }),
        );

        const store = useJobStore();
        store.pollJobUntilTerminal({ id: "job5", full: false });
        await flushPromises();
        expect(callCount).toBe(1);
        expect(lastFullParam).toBe("false");

        // A full: true caller arrives while that poll is still active (job still running) --
        // rather than starting a second loop, it should upgrade the existing one in place.
        store.pollJobUntilTerminal({ id: "job5", full: true });
        await flushPromises();
        expect(callCount).toBe(1); // no immediate second fetch, just flags the running loop

        await advanceTimersAndFlush(1000);
        expect(callCount).toBe(2);
        expect(lastFullParam).toBe("true");
    });

    it("merges a base response into an already-cached full job instead of overwriting it", async () => {
        server.use(
            http.get("/api/jobs/{job_id}", ({ response, request }) => {
                const full = new URL(request.url).searchParams.get("full") === "true";
                if (full) {
                    return response(200).json({
                        ...buildJob("job8", "running"),
                        stdout: "full stdout",
                        stderr: "full stderr",
                    });
                }
                // A base (`full=false`) response never carries `stdout`/`stderr` at all -- they're
                // not merely empty, they're absent from this (differently-shaped) response.
                const { stdout: _stdout, stderr: _stderr, ...baseJob } = buildJob("job8", "running");
                return response(200).json(baseJob);
            }),
        );

        const store = useJobStore();
        await store.fetchJob({ id: "job8", full: true });
        expect(store.getJob("job8")?.stdout).toBe("full stdout");

        // A later base fetch for the same id (e.g. a second, non-full caller) must not clobber
        // the full-only fields already cached.
        await store.fetchJob({ id: "job8", full: false });
        expect(store.getJob("job8")?.stdout).toBe("full stdout");
        expect(store.getJob("job8")?.stderr).toBe("full stderr");
        // The base response's own fields (e.g. `state`) still come through fresh.
        expect(store.getJob("job8")?.state).toBe("running");
    });

    it("does not let a full: true request piggyback on a concurrent in-flight full: false request", async () => {
        let callCount = 0;
        const fullParamsByCall: (string | null)[] = [];
        let resolveBaseFetch: (() => void) | undefined;
        server.use(
            http.get("/api/jobs/{job_id}", async ({ response, request }) => {
                callCount++;
                const full = new URL(request.url).searchParams.get("full");
                fullParamsByCall.push(full);
                if (full === "false") {
                    // Hold the base request open so a full: true request can race it.
                    await new Promise<void>((resolve) => {
                        resolveBaseFetch = resolve;
                    });
                }
                return response(200).json(buildJob("job6", "ok"));
            }),
        );

        const store = useJobStore();
        // Kick off a base fetch and let it start (but not finish) before the full fetch begins.
        const basePromise = store.fetchJob({ id: "job6", full: false });
        await flushPromises();
        expect(callCount).toBe(1);

        // While the base fetch is still in flight, a full fetch for the same id comes in -- it
        // must not be satisfied by the base fetch's (still pending) in-flight promise/result.
        const fullPromise = store.fetchJob({ id: "job6", full: true });

        resolveBaseFetch?.();
        await Promise.all([basePromise, fullPromise]);

        expect(callCount).toBe(2);
        expect(fullParamsByCall).toEqual(["false", "true"]);
    });

    it("still fetches full once more if the poll was upgraded after an in-flight base tick already started", async () => {
        let callCount = 0;
        const fullParamsByCall: (string | null)[] = [];
        let resolveBaseTick: (() => void) | undefined;
        server.use(
            http.get("/api/jobs/{job_id}", async ({ response, request }) => {
                callCount++;
                const full = new URL(request.url).searchParams.get("full");
                fullParamsByCall.push(full);
                // The first tick reports the job still running, so the poll schedules a second
                // tick; the second tick (still base, since the upgrade hasn't landed yet) is held
                // open so the upgrade below can land while it's in flight, then reports terminal.
                if (full === "false" && callCount === 2) {
                    await new Promise<void>((resolve) => {
                        resolveBaseTick = resolve;
                    });
                    return response(200).json(buildJob("job7", "ok"));
                }
                return response(200).json(buildJob("job7", "running"));
            }),
        );

        const store = useJobStore();
        store.pollJobUntilTerminal({ id: "job7", full: false });
        await flushPromises();
        expect(callCount).toBe(1);

        // Start the loop's next tick (still base, since it reads `full` before the upgrade below).
        await advanceTimersAndFlush(1000);
        expect(callCount).toBe(2);

        // The upgrade arrives while that base tick is still in flight.
        store.pollJobUntilTerminal({ id: "job7", full: true });

        // Let the held-open base tick resolve (terminal). It must not stop polling having only
        // ever fetched the base representation -- it should fetch full once more first.
        resolveBaseTick?.();
        await flushPromises();
        expect(callCount).toBe(3);
        expect(fullParamsByCall[2]).toBe("true");

        expect(store.getJob("job7")).not.toBeNull();
    });

    it("stops polling for good after a non-retryable fetch error (e.g. a malformed job id)", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                callCount++;
                return response("4XX").json(
                    { err_msg: "Wrong id specified, unable to decode.", err_code: 400 },
                    { status: 400 },
                );
            }),
        );

        const store = useJobStore();
        store.pollJobUntilTerminal({ id: "bad-id" });
        await flushPromises();
        expect(callCount).toBe(1);

        // A 400 will never succeed no matter how many times we ask -- must not keep polling.
        await advanceTimersAndFlush(5000);
        expect(callCount).toBe(1);
    });

    it("stops polling once a retryable fetch error has exhausted its retries", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                callCount++;
                return response("5XX").json({ err_msg: "Server error", err_code: 500 }, { status: 500 });
            }),
        );

        const store = useJobStore();
        store.pollJobUntilTerminal({ id: "flaky-id" });
        await flushPromises();
        expect(callCount).toBe(1);

        // Keeps retrying a transient-looking error for a while...
        await advanceTimersAndFlush(1000);
        await advanceTimersAndFlush(1000);
        await advanceTimersAndFlush(1000);
        expect(callCount).toBeGreaterThan(1);

        const callsAfterRetries = callCount;
        // ...but eventually gives up rather than retrying forever.
        await advanceTimersAndFlush(1000);
        await advanceTimersAndFlush(1000);
        await advanceTimersAndFlush(1000);
        expect(callCount).toBe(callsAfterRetries);
    });
});

describe("useJobStore eviction", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    afterEach(() => {
        vi.clearAllTimers();
    });

    it("evicts unused jobs while retaining displayed terminal jobs", async () => {
        server.use(
            http.get("/api/jobs/{job_id}", ({ response, params }) =>
                response(200).json(buildJob(params.job_id as string, "ok")),
            ),
        );
        const store = useJobStore();
        const release = store.retainJob("displayed");
        await store.fetchJob({ id: "displayed" });
        await pollManyJobs(
            store,
            Array.from({ length: MAX_CACHED_JOBS }, (_, i) => `job-${i}`),
        );

        expect(store.getCachedJob("job-0")).toBeNull();
        expect(store.getCachedJob(`job-${MAX_CACHED_JOBS - 1}`)?.state).toBe("ok");
        expect(store.getCachedJob("displayed")?.state).toBe("ok");

        release();
        await pollManyJobs(
            store,
            Array.from({ length: MAX_CACHED_JOBS }, (_, i) => `next-${i}`),
        );
        expect(store.getCachedJob("displayed")).toBeNull();
    });

    it("never evicts a job that is still actively being polled", async () => {
        let runningJobCallCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response, params }) => {
                if (params.job_id === "still-running") {
                    runningJobCallCount++;
                    return response(200).json(buildJob("still-running", "running"));
                }
                return response(200).json(buildJob(params.job_id as string, "ok"));
            }),
        );

        const store = useJobStore();

        // Start a poll for a non-terminal job first, so it's the oldest entry once the cache
        // fills up with terminal jobs after it.
        const { stopWatchingJob } = store.pollJobUntilTerminal({ id: "still-running" });
        await flushPromises();
        expect(runningJobCallCount).toBe(1);

        await pollManyJobs(
            store,
            Array.from({ length: MAX_CACHED_JOBS }, (_, i) => `job-${i}`),
        );

        // Despite being the least-recently-touched entry, "still-running" must survive because
        // it's still actively polled -- evicting it would silently stop a live poll's caller
        // from ever seeing further updates.
        expect(store.getJob("still-running")).not.toBeNull();

        await advanceTimersAndFlush(1000);
        expect(runningJobCallCount).toBe(2);

        stopWatchingJob();
    });
});

describe("full job freshness", () => {
    beforeEach(() => setActivePinia(createPinia()));
    afterEach(() => vi.clearAllTimers());

    it("fetches final full details after a base poll observes completion", async () => {
        let completed = false;
        const fullRequests: boolean[] = [];
        server.use(
            http.get("/api/jobs/{job_id}", ({ response, request }) => {
                const full = new URL(request.url).searchParams.get("full") === "true";
                fullRequests.push(full);
                const job = buildJob("job", completed ? "ok" : "running");
                return response(200).json(full ? { ...job, tool_stdout: completed ? "final output" : "" } : job);
            }),
        );
        const store = useJobStore();
        await store.fetchJob({ id: "job", full: true });
        completed = true;
        store.pollJobUntilTerminal({ id: "job", full: false });
        await flushPromises();
        store.pollJobUntilTerminal({ id: "job", full: true });
        await flushPromises();

        expect(store.getCachedJob("job")?.tool_stdout).toBe("final output");
        expect(fullRequests).toEqual([true, false, true]);
        store.pollJobUntilTerminal({ id: "job", full: true });
        await flushPromises();
        expect(fullRequests).toEqual([true, false, true]);
    });

    it("retries a failed full upgrade instead of caching incomplete terminal details", async () => {
        let fullCalls = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response, request }) => {
                if (new URL(request.url).searchParams.get("full") === "true") {
                    fullCalls++;
                    if (fullCalls === 1) {
                        return response("5XX").json(
                            { err_msg: "Temporarily unavailable", err_code: 503 },
                            { status: 503 },
                        );
                    }
                    return response(200).json({ ...buildJob("job", "ok"), tool_stdout: "final output" });
                }
                return response(200).json(buildJob("job", "ok"));
            }),
        );
        const store = useJobStore();
        await store.fetchJob({ id: "job", full: false });
        store.pollJobUntilTerminal({ id: "job", full: true });
        await flushPromises();
        expect(store.getJobLoadError("job")).toBeTruthy();
        await advanceTimersAndFlush(1000);
        expect(store.getCachedJob("job")?.tool_stdout).toBe("final output");
        expect(store.getJobLoadError("job")).toBeNull();
        await advanceTimersAndFlush(1000);
        expect(fullCalls).toBe(2);
    });
});
