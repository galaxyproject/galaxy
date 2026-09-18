import { createTestingPinia } from "@pinia/testing";
import { advanceTimersAndFlush } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, type Ref, ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type { JobState, ShowFullJobResponse } from "@/api/jobs";

import { useJobDetails } from "./jobDetails";

const { server, http } = useServerMock();

vi.useFakeTimers();

function buildJob(id: string, state: JobState, overrides: Partial<ShowFullJobResponse> = {}): ShowFullJobResponse {
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
        ...overrides,
    } as ShowFullJobResponse;
}

function mountJobDetails(jobId: Ref<string | undefined>, options?: { autoRefresh?: boolean; full?: boolean }) {
    const mounted = {
        job: ref<ShowFullJobResponse | null>(null),
        error: ref<unknown>(null),
        loading: ref(false),
    };

    const TestComponent = defineComponent({
        setup() {
            Object.assign(mounted, useJobDetails(jobId, options));
            return () => null;
        },
    });

    const wrapper = mount(TestComponent);
    return { ...mounted, wrapper };
}

describe("useJobDetails", () => {
    beforeEach(() => {
        setActivePinia(createTestingPinia({ createSpy: vi.fn, stubActions: false }));
    });

    afterEach(() => {
        vi.clearAllTimers();
    });

    it("fetches the job on mount and exposes it reactively", async () => {
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                return response(200).json(buildJob("job1", "running"));
            }),
        );

        const jobId = ref<string | undefined>("job1");
        const { job } = mountJobDetails(jobId);

        expect(job.value).toBeNull();
        await flushPromises();

        expect(job.value?.id).toBe("job1");
        expect(job.value?.state).toBe("running");
    });

    it("keeps polling while the job is in a non-terminal state", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                callCount++;
                return response(200).json(buildJob("job1", "running"));
            }),
        );

        const jobId = ref<string | undefined>("job1");
        mountJobDetails(jobId);
        await flushPromises();
        expect(callCount).toBe(1);

        await advanceTimersAndFlush(1000);
        expect(callCount).toBe(2);

        await advanceTimersAndFlush(1000);
        expect(callCount).toBe(3);
    });

    it("stops polling once the job reaches a terminal state", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                callCount++;
                // Terminal on the very first response.
                return response(200).json(buildJob("job1", "ok"));
            }),
        );

        const jobId = ref<string | undefined>("job1");
        const { job } = mountJobDetails(jobId);
        await flushPromises();

        expect(job.value?.state).toBe("ok");
        expect(callCount).toBe(1);

        await advanceTimersAndFlush(5000);
        expect(callCount).toBe(1);
    });

    it("does not fetch or poll when jobId is undefined", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                callCount++;
                return response(200).json(buildJob("job1", "running"));
            }),
        );

        const jobId = ref<string | undefined>(undefined);
        const { job } = mountJobDetails(jobId);
        await flushPromises();

        expect(job.value).toBeNull();
        expect(callCount).toBe(0);
    });

    it("surfaces a load error", async () => {
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                return response("4XX").json({ err_msg: "not found", err_code: 404 }, { status: 404 });
            }),
        );

        const jobId = ref<string | undefined>("job1");
        const { job, error } = mountJobDetails(jobId);
        await flushPromises();

        expect(job.value).toBeNull();
        expect(error.value).toBeTruthy();
    });

    it("stops polling once the consuming component unmounts", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                callCount++;
                return response(200).json(buildJob("job1", "running"));
            }),
        );

        const jobId = ref<string | undefined>("job1");
        const { wrapper } = mountJobDetails(jobId);
        await flushPromises();
        expect(callCount).toBe(1);

        await advanceTimersAndFlush(1000);
        expect(callCount).toBe(2);

        wrapper.destroy();

        // With the poller stopped, further time passing must not produce any more requests,
        // otherwise it would keep hitting the server for the rest of the session even though
        // nothing is displaying this job anymore.
        await advanceTimersAndFlush(5000);
        expect(callCount).toBe(2);
    });

    it("stops the previous job's poll when jobId changes to a different job", async () => {
        let job1Calls = 0;
        let job2Calls = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response, params }) => {
                if (params.job_id === "job1") {
                    job1Calls++;
                    return response(200).json(buildJob("job1", "running"));
                }
                job2Calls++;
                return response(200).json(buildJob("job2", "running"));
            }),
        );

        const jobId = ref<string | undefined>("job1");
        mountJobDetails(jobId);
        await flushPromises();
        expect(job1Calls).toBe(1);

        jobId.value = "job2";
        await flushPromises();
        expect(job2Calls).toBe(1);

        // job1's poll must have been released when we switched away from it, not left running
        // alongside job2's.
        await advanceTimersAndFlush(1000);
        expect(job1Calls).toBe(1);
        expect(job2Calls).toBe(2);
    });

    it("keeps polling a shared job alive until every consumer has unmounted", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => {
                callCount++;
                return response(200).json(buildJob("job1", "running"));
            }),
        );

        const jobId = ref<string | undefined>("job1");
        const first = mountJobDetails(jobId);
        const second = mountJobDetails(jobId);
        await flushPromises();
        expect(callCount).toBe(1); // jobStore dedupes the actual request across both consumers

        first.wrapper.destroy();

        // The second consumer is still mounted and interested, so the poll must keep going.
        await advanceTimersAndFlush(1000);
        expect(callCount).toBe(2);

        second.wrapper.destroy();

        // Now that both consumers are gone, the poll must actually stop.
        await advanceTimersAndFlush(5000);
        expect(callCount).toBe(2);
    });
});
