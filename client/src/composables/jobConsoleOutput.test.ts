import { createTestingPinia } from "@pinia/testing";
import { advanceTimersAndFlush } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, type Ref, ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type { JobConsoleOutput } from "@/api/jobs";

import { useJobConsoleOutput } from "./jobDetails";

const { server, http } = useServerMock();

vi.useFakeTimers();

function buildConsoleOutput(overrides: Partial<JobConsoleOutput> = {}): JobConsoleOutput {
    return { state: "running", stdout: "", stderr: "", ...overrides };
}

function mountJobConsoleOutput(jobId: Ref<string | undefined>) {
    const mounted = {
        stdout: ref(""),
        stderr: ref(""),
        error: ref<unknown>(null),
    };

    const TestComponent = defineComponent({
        setup() {
            Object.assign(mounted, useJobConsoleOutput(jobId));
            return () => null;
        },
    });

    const wrapper = mount(TestComponent);
    return { ...mounted, wrapper };
}

describe("useJobConsoleOutput", () => {
    beforeEach(() => {
        setActivePinia(createTestingPinia({ createSpy: vi.fn, stubActions: false }));
    });

    afterEach(() => {
        vi.clearAllTimers();
    });

    it("accumulates stdout/stderr across polls", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}/console_output", ({ response }) => {
                callCount++;
                if (callCount === 1) {
                    return response(200).json(buildConsoleOutput({ stdout: "line1\n", stderr: "" }));
                }
                return response(200).json(buildConsoleOutput({ stdout: "line2\n", stderr: "warn\n" }));
            }),
        );

        const jobId = ref<string | undefined>("job1");
        const { stdout, stderr } = mountJobConsoleOutput(jobId);
        await flushPromises();

        expect(stdout.value).toBe("line1\n");
        expect(stderr.value).toBe("");

        await advanceTimersAndFlush(3000);
        expect(stdout.value).toBe("line1\nline2\n");
        expect(stderr.value).toBe("warn\n");
    });

    it("stops polling once the job's console state is terminal", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}/console_output", ({ response }) => {
                callCount++;
                return response(200).json(buildConsoleOutput({ state: "ok", stdout: "done\n" }));
            }),
        );

        const jobId = ref<string | undefined>("job1");
        const { stdout } = mountJobConsoleOutput(jobId);
        await flushPromises();

        expect(stdout.value).toBe("done\n");
        expect(callCount).toBe(1);

        await advanceTimersAndFlush(5000);
        expect(callCount).toBe(1);
    });

    it("resets accumulated output when jobId changes", async () => {
        server.use(
            http.get("/api/jobs/{job_id}/console_output", ({ params, response }) => {
                const id = params.job_id;
                return response(200).json(buildConsoleOutput({ stdout: `output for ${id}\n` }));
            }),
        );

        const jobId = ref<string | undefined>("job1");
        const { stdout } = mountJobConsoleOutput(jobId);
        await flushPromises();
        expect(stdout.value).toBe("output for job1\n");

        jobId.value = "job2";
        await flushPromises();
        expect(stdout.value).toBe("output for job2\n");
    });

    it("does not fetch when jobId is undefined", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}/console_output", ({ response }) => {
                callCount++;
                return response(200).json(buildConsoleOutput());
            }),
        );

        const jobId = ref<string | undefined>(undefined);
        const { stdout } = mountJobConsoleOutput(jobId);
        await flushPromises();

        expect(stdout.value).toBe("");
        expect(callCount).toBe(0);
    });

    it("stops polling once the consuming component unmounts", async () => {
        let callCount = 0;
        server.use(
            http.get("/api/jobs/{job_id}/console_output", ({ response }) => {
                callCount++;
                return response(200).json(buildConsoleOutput({ stdout: "line\n" }));
            }),
        );

        const jobId = ref<string | undefined>("job1");
        const { wrapper } = mountJobConsoleOutput(jobId);
        await flushPromises();
        expect(callCount).toBe(1);

        wrapper.unmount();

        await advanceTimersAndFlush(5000);
        expect(callCount).toBe(1);
    });

    it("ignores a stale response from a previous visit to the same job id", async () => {
        // job1's first fetch is held open so it resolves only after we've switched away and back
        // to job1, by which point it's a leftover from an earlier visit, not the current one.
        let resolveFirstFetchForJob1: (output: JobConsoleOutput) => void;
        let sawFirstFetchForJob1 = false;
        server.use(
            http.get("/api/jobs/{job_id}/console_output", ({ response, params }) => {
                if (params.job_id === "job1" && !sawFirstFetchForJob1) {
                    sawFirstFetchForJob1 = true;
                    return new Promise((resolve) => {
                        resolveFirstFetchForJob1 = (output) => resolve(response(200).json(output));
                    });
                }
                if (params.job_id === "job1") {
                    return response(200).json(buildConsoleOutput({ stdout: "second visit to job1\n" }));
                }
                return response(200).json(buildConsoleOutput({ stdout: "job2 output\n" }));
            }),
        );

        const jobId = ref<string | undefined>("job1");
        const { stdout, wrapper } = mountJobConsoleOutput(jobId);
        await flushPromises();

        // Switch away to job2 (its own fetch resolves normally) and then back to job1, all while
        // job1's first fetch above is still pending.
        jobId.value = "job2";
        await flushPromises();

        jobId.value = "job1";
        await flushPromises();

        // The stale response from job1's first visit arrives now. It must not be appended.
        resolveFirstFetchForJob1!(buildConsoleOutput({ stdout: "stale, from the first visit to job1\n" }));
        await flushPromises();

        expect(stdout.value).toBe("second visit to job1\n");
        wrapper.unmount();
    });
});
