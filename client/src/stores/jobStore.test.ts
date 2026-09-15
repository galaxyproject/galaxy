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

    it("allows polling again for the same id after it previously stopped", async () => {
        let state: JobState = "ok";
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                callCount++;
                return response(200).json(buildJob("job1", state));
            }),
        );

        const store = useJobStore();
        store.pollJobUntilTerminal({ id: "job1" });
        await flushPromises();
        expect(callCount).toBe(1);

        // Let the loop's next tick see the terminal state and clean itself up.
        await advanceTimersAndFlush(1000);
        expect(callCount).toBe(1); // still terminal, no second fetch from that loop

        state = "running";
        store.pollJobUntilTerminal({ id: "job1" });
        await flushPromises();
        expect(callCount).toBe(2);
    });
});
