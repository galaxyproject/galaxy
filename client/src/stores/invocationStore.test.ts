import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { StepJobSummary, WorkflowJobMetric } from "@/api/invocations";

import { useInvocationStore } from "./invocationStore";

const { server, http } = useServerMock();

function stepJobsSummaryResponse(states: Record<string, number>): StepJobSummary[] {
    return [{ id: "step1", model: "ImplicitCollectionJobs", states } as unknown as StepJobSummary];
}

function metricsResponse(jobIds: string[]): WorkflowJobMetric[] {
    return jobIds.map(
        (job_id) =>
            ({
                plugin: "core",
                name: "runtime_seconds",
                title: "Job Runtime",
                value: `${job_id}-runtime`,
                raw_value: "1",
                job_id,
            }) as unknown as WorkflowJobMetric,
    );
}

describe("stores/invocationStore", () => {
    let stepJobsSummary: StepJobSummary[];
    let metricsCallCount: number;

    beforeEach(() => {
        setActivePinia(createPinia());

        stepJobsSummary = stepJobsSummaryResponse({ running: 1 });
        metricsCallCount = 0;

        server.use(
            http.get("/api/invocations/{invocation_id}/step_jobs_summary", ({ response }) => {
                return response(200).json(stepJobsSummary);
            }),
            http.get("/api/invocations/{invocation_id}/metrics", ({ response }) => {
                metricsCallCount++;
                return response(200).json(metricsResponse(["job1"]));
            }),
        );
    });

    describe("getInvocationMetricsById", () => {
        it("fetches once for a given invocation id and reuses the cached result", async () => {
            const store = useInvocationStore();

            store.getInvocationMetricsById("inv1");
            store.getInvocationMetricsById("inv1");
            await flushPromises();

            expect(metricsCallCount).toBe(1);
        });

        it("refetches once a step's terminal job count increases since the last fetch", async () => {
            const store = useInvocationStore();

            // Initial fetch, with one job still running (nothing terminal yet).
            store.getInvocationMetricsById("inv1");
            await flushPromises();
            expect(metricsCallCount).toBe(1);

            // A job in the collection finishes -- terminal count for the step goes from 0 to 1.
            // (Refreshed explicitly, mirroring the polling loop in WorkflowInvocationState.vue that
            // keeps the step jobs summary cache up to date independently of the metrics fetch.)
            stepJobsSummary = stepJobsSummaryResponse({ running: 1, ok: 1 });
            await store.fetchInvocationStepJobsSummaryForId({ id: "inv1" });

            store.getInvocationMetricsById("inv1");
            await flushPromises();

            expect(metricsCallCount).toBe(2);
        });

        it("does not refetch when the terminal job count is unchanged", async () => {
            stepJobsSummary = stepJobsSummaryResponse({ ok: 1, running: 1 });

            const store = useInvocationStore();

            store.getInvocationMetricsById("inv1");
            await flushPromises();
            expect(metricsCallCount).toBe(1);

            // Step jobs summary is refreshed but reports the same states -- no newly-terminal jobs.
            await store.fetchInvocationStepJobsSummaryForId({ id: "inv1" });

            store.getInvocationMetricsById("inv1");
            await flushPromises();

            expect(metricsCallCount).toBe(1);
        });
    });

    describe("getInvocationJobRuntimeById", () => {
        it("maps job ids to their runtime_seconds metric value", async () => {
            const store = useInvocationStore();

            store.getInvocationMetricsById("inv1");
            await flushPromises();

            expect(store.getInvocationJobRuntimeById("inv1")).toEqual({ job1: "job1-runtime" });
        });

        it("returns an empty lookup before metrics have loaded", () => {
            const store = useInvocationStore();

            expect(store.getInvocationJobRuntimeById("inv1")).toEqual({});
        });
    });
});
