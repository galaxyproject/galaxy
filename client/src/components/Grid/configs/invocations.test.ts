import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useHistoryStore } from "@/stores/historyStore";
import { useWorkflowStore } from "@/stores/workflowStore";

import { getData } from "./invocations";

const { server, http } = useServerMock();

const INVOCATIONS = [
    { id: "inv-1", workflow_id: "instance-a", history_id: "history-1", state: "scheduled" },
    { id: "inv-2", workflow_id: "instance-a", history_id: "history-1", state: "scheduled" },
    { id: "inv-3", workflow_id: "instance-b", history_id: "history-2", state: "scheduled" },
    { id: "inv-4", workflow_id: "instance-b", history_id: "history-2", state: "scheduled" },
];

const workflowRequests = vi.fn();
const historyRequests = vi.fn();
const invocationQueries = vi.fn();

function mockServer(workflowFails = false, historyFails = false) {
    server.use(
        http.get("/api/invocations", ({ request, response }) => {
            const searchParams = new URL(request.url).searchParams;
            invocationQueries({
                workflow_id: searchParams.getAll("workflow_id"),
                history_id: searchParams.getAll("history_id"),
                user_id: searchParams.get("user_id"),
            });
            return response.untyped(HttpResponse.json(INVOCATIONS, { headers: { total_matches: "4" } }));
        }),
        http.get("/api/histories/{history_id}", ({ params, response }) => {
            historyRequests(params.history_id);
            if (historyFails) {
                return response.untyped(HttpResponse.error());
            }
            return response.untyped(HttpResponse.json({ id: params.history_id, name: `History ${params.history_id}` }));
        }),
        http.get("/api/workflows/{workflow_id}", ({ params, response }) => {
            workflowRequests(params.workflow_id);
            if (workflowFails) {
                return response("5XX").json({ err_msg: "Request failed", err_code: 500 }, { status: 500 });
            }
            return response.untyped(
                HttpResponse.json({ id: `stored-${params.workflow_id}`, name: `Workflow ${params.workflow_id}` }),
            );
        }),
    );
}

describe("invocations grid getData", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        workflowRequests.mockReset();
        historyRequests.mockReset();
        invocationQueries.mockReset();
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.useRealTimers();
    });

    it("requests each workflow and history once, regardless of row count or repeated loads", async () => {
        mockServer();

        await Promise.all([getData(0, 25, "", "create_time", true), getData(0, 20, "", "create_time", true)]);
        await flushPromises();
        await getData(0, 25, "", "create_time", true);
        await flushPromises();

        expect(workflowRequests).toHaveBeenCalledTimes(2);
        expect(workflowRequests.mock.calls.map(([id]) => id).sort()).toEqual(["instance-a", "instance-b"]);
        expect(useWorkflowStore().getStoredWorkflowNameByInstanceId("instance-a")).toBe("Workflow instance-a");
        expect(historyRequests.mock.calls.map(([id]) => id).sort()).toEqual(["history-1", "history-2"]);
        expect(useHistoryStore().getHistoryById("history-1", false)?.name).toBe("History history-1");
    });

    it("handles failed workflow fetches without unhandled rejections", async () => {
        mockServer(true);
        const consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

        const [data] = await getData(0, 25, "", "create_time", true);
        await flushPromises();

        expect(data).toHaveLength(4);
        expect(workflowRequests).toHaveBeenCalledTimes(2);
        expect(consoleWarnSpy).toHaveBeenCalledWith("Failed to load workflow instance-a", expect.any(Error));
        expect(useWorkflowStore().getStoredWorkflowNameByInstanceId("instance-a")).toBe("...");
        consoleWarnSpy.mockRestore();
    });

    it("does not re-request failing histories on reload while they back off", async () => {
        vi.useFakeTimers();
        mockServer(false, true);
        vi.spyOn(console, "warn").mockImplementation(() => {});

        await getData(0, 25, "", "create_time", true);
        await flushPromises();
        expect(historyRequests).toHaveBeenCalledTimes(2);

        await getData(0, 25, "", "create_time", true);
        await flushPromises();
        expect(historyRequests).toHaveBeenCalledTimes(2);
    });
});

describe("invocations grid filtering", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        invocationQueries.mockReset();
    });

    it("sends every matching workflow id and the picked history ids", async () => {
        mockServer();
        server.use(
            http.get("/api/workflows", ({ request, response }) => {
                const search = new URL(request.url).searchParams.get("search");
                const items = search === "name:rna" ? [{ id: "workflow-1" }, { id: "workflow-2" }] : [];
                return response.untyped(HttpResponse.json(items, { headers: { total_matches: String(items.length) } }));
            }),
        );

        const [data, total] = await getData(
            0,
            25,
            "rna history_id:1cd8e2f6b131e891,f2db41e1fa331b3e",
            "create_time",
            true,
            { user_id: "user-1" },
        );

        expect(data).toHaveLength(4);
        expect(total).toBe(4);
        expect(invocationQueries).toHaveBeenCalledWith({
            workflow_id: ["workflow-1", "workflow-2"],
            history_id: ["1cd8e2f6b131e891", "f2db41e1fa331b3e"],
            user_id: "user-1",
        });
    });

    it("skips the invocation request when a name matches nothing", async () => {
        mockServer();
        server.use(
            http.get("/api/workflows", ({ response }) => {
                return response.untyped(HttpResponse.json([], { headers: { total_matches: "0" } }));
            }),
        );

        const [data, total] = await getData(0, 25, "workflow:missing", "create_time", true);

        expect(data).toEqual([]);
        expect(total).toBe(0);
        expect(invocationQueries).not.toHaveBeenCalled();
    });
});
