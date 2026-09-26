import { advanceTimersAndFlush } from "@tests/vitest/helpers";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { JobState, ShowFullJobResponse } from "@/api/jobs";

import { MAX_CACHED_JOBS, useJobStore } from "./jobStore";

const { server, http } = useServerMock();

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

    it("evicts the least-recently-touched terminal job once the cache exceeds its cap", async () => {
        const callCounts: Record<string, number> = {};
        server.use(
            http.get("/api/jobs/{job_id}", ({ response, params }) => {
                const id = params.job_id as string;
                callCounts[id] = (callCounts[id] ?? 0) + 1;
                return response(200).json(buildJob(id, "ok"));
            }),
        );

        const store = useJobStore();

        // Fill the cache to exactly its cap. job-0 is the oldest entry, never touched again below.
        await pollManyJobs(
            store,
            Array.from({ length: MAX_CACHED_JOBS }, (_, i) => `job-${i}`),
        );
        expect(callCounts["job-0"]).toBe(1);

        // One more distinct job pushes the cache over the cap.
        store.pollJobUntilTerminal({ id: "job-overflow" });
        await flushPromises();
        expect(callCounts["job-overflow"]).toBe(1);

        // job-0 was the least-recently-touched entry and should have been evicted -- reading it
        // again now must trigger a fresh fetch rather than being satisfied by the (removed) cache
        // entry, since a cached+terminal job would otherwise never be re-fetched.
        store.pollJobUntilTerminal({ id: "job-0" });
        await flushPromises();
        expect(callCounts["job-0"]).toBe(2);

        // The most recently added (still-cached) job, by contrast, is not re-fetched.
        store.pollJobUntilTerminal({ id: `job-${MAX_CACHED_JOBS - 1}` });
        await flushPromises();
        expect(callCounts[`job-${MAX_CACHED_JOBS - 1}`]).toBe(1);
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
        store.pollJobUntilTerminal({ id: "still-running" });
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
    });
});
