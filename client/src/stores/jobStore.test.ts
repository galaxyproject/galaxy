import { advanceTimersAndFlush } from "@tests/vitest/helpers";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { JobState, ShowFullJobResponse } from "@/api/jobs";

import { useJobStore } from "./jobStore";

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
});
