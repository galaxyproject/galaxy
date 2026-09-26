import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type {
    StepJobSummary,
    WorkflowInvocation,
    WorkflowInvocationElementView,
    WorkflowJobMetric,
} from "@/api/invocations";

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

function invocationResponse(id: string, updateTime: string): WorkflowInvocation {
    return {
        id,
        create_time: updateTime,
        update_time: updateTime,
        state: "scheduled",
        history_id: `history-${id}`,
        workflow_id: `workflow-${id}`,
        model_class: "WorkflowInvocation",
    } as unknown as WorkflowInvocation;
}

/** The element view served by `GET /api/invocations/{invocation_id}`, unlike the index's collection view. */
function invocationDetailsResponse(id: string, updateTime: string): WorkflowInvocationElementView {
    return {
        ...invocationResponse(id, updateTime),
        steps: [{ id: `step-${id}` }],
        inputs: {},
        input_step_parameters: {},
        outputs: {},
        output_collections: {},
        output_values: {},
        messages: [],
    } as unknown as WorkflowInvocationElementView;
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

    describe("fetchLatestInvocations", () => {
        let invocations: WorkflowInvocation[];
        let invocationsCallCount: number;
        let requestedLimits: (string | null)[];

        beforeEach(() => {
            invocations = [invocationResponse("inv2", "2026-08-02"), invocationResponse("inv1", "2026-08-01")];
            invocationsCallCount = 0;
            requestedLimits = [];

            server.use(
                http.get("/api/invocations", ({ response, request }) => {
                    invocationsCallCount++;
                    requestedLimits.push(new URL(request.url).searchParams.get("limit"));
                    return response(200).json(invocations);
                }),
                // Requested by the grid's `getData` to populate the name caches.
                http.get("/api/histories/{history_id}", ({ response, params }) => {
                    return response(200).json({ id: params.history_id, name: "History" } as never);
                }),
                http.get("/api/workflows/{workflow_id}", ({ response, params }) => {
                    return response(200).json({ id: params.workflow_id, name: "Workflow" } as never);
                }),
            );
        });

        it("stores the latest invocations in server order and exposes them as summaries", async () => {
            const store = useInvocationStore();

            const fetched = await store.fetchLatestInvocations();

            expect(fetched.map((invocation) => invocation.id)).toEqual(["inv2", "inv1"]);
            expect(store.latestInvocations.map((invocation) => invocation.id)).toEqual(["inv2", "inv1"]);
            expect(requestedLimits).toEqual(["15"]);
        });

        it("passes the requested limit on to the server", async () => {
            const store = useInvocationStore();

            await store.fetchLatestInvocations(5);

            expect(requestedLimits).toEqual(["5"]);
        });

        it("merges the fetched invocations into the shared cache instead of duplicating them", async () => {
            const store = useInvocationStore();

            await store.fetchLatestInvocations();
            store.updateInvocation("inv1", { state: "cancelled" });

            expect(store.getInvocationById("inv1")?.state).toBe("cancelled");
            expect(store.latestInvocations.find((invocation) => invocation.id === "inv1")?.state).toBe("cancelled");
            expect(store.sortedStoredInvocations.map((invocation) => invocation.id)).toEqual(["inv2", "inv1"]);
        });

        it("dedupes repeated ids and replaces the previous list on refetch", async () => {
            const store = useInvocationStore();

            invocations = [invocationResponse("inv1", "2026-08-01"), invocationResponse("inv1", "2026-08-01")];
            await store.fetchLatestInvocations();
            expect(store.latestInvocations.map((invocation) => invocation.id)).toEqual(["inv1"]);

            invocations = [invocationResponse("inv3", "2026-08-03")];
            await store.fetchLatestInvocations();
            expect(store.latestInvocations.map((invocation) => invocation.id)).toEqual(["inv3"]);
        });

        it("shares a single request between concurrent calls", async () => {
            const store = useInvocationStore();

            await Promise.all([store.fetchLatestInvocations(), store.fetchLatestInvocations()]);

            expect(invocationsCallCount).toBe(1);
            expect(store.isLoadingLatestInvocations).toBe(false);
        });

        it("resets the loading flag and allows retrying after a failed fetch", async () => {
            const store = useInvocationStore();

            server.use(
                http.get("/api/invocations", ({ response }) => {
                    invocationsCallCount++;
                    return response("4XX").json({ err_msg: "nope", err_code: 400 }, { status: 400 });
                }),
            );
            await expect(store.fetchLatestInvocations()).rejects.toBeDefined();
            expect(store.isLoadingLatestInvocations).toBe(false);

            server.use(
                http.get("/api/invocations", ({ response }) => {
                    invocationsCallCount++;
                    return response(200).json(invocations);
                }),
            );
            await store.fetchLatestInvocations();

            expect(invocationsCallCount).toBe(2);
            expect(store.latestInvocations.map((invocation) => invocation.id)).toEqual(["inv2", "inv1"]);
        });

        describe("getInvocationById", () => {
            let requestedDetailIds: string[];

            beforeEach(() => {
                requestedDetailIds = [];

                server.use(
                    http.get("/api/invocations/{invocation_id}", ({ response, params }) => {
                        requestedDetailIds.push(params.invocation_id);
                        return response(200).json(invocationDetailsResponse(params.invocation_id, "2026-08-01"));
                    }),
                );
            });

            it("fetches the details of an invocation that is only cached as a list summary", async () => {
                const store = useInvocationStore();

                await store.fetchLatestInvocations();
                expect(requestedDetailIds).toEqual([]);

                expect(store.getInvocationById("inv1")).not.toHaveProperty("steps");
                await flushPromises();

                expect(requestedDetailIds).toEqual(["inv1"]);
                expect(store.getInvocationById("inv1")).toHaveProperty("steps", [{ id: "step-inv1" }]);
            });

            it("does not refetch an invocation whose details are already cached", async () => {
                const store = useInvocationStore();

                await store.fetchLatestInvocations();
                store.getInvocationById("inv1");
                await flushPromises();

                store.getInvocationById("inv1");
                await flushPromises();

                expect(requestedDetailIds).toEqual(["inv1"]);
            });

            it("keeps cached details when a list summary for the same invocation arrives later", async () => {
                const store = useInvocationStore();

                await store.fetchInvocationById({ id: "inv1" });
                await store.fetchLatestInvocations();

                const invocation = store.latestInvocations.find((item) => item.id === "inv1");
                expect(invocation).toHaveProperty("steps", [{ id: "step-inv1" }]);
                expect(store.getInvocationById("inv1")).toHaveProperty("steps", [{ id: "step-inv1" }]);
                await flushPromises();

                expect(requestedDetailIds).toEqual(["inv1"]);
            });
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
