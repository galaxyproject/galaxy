import { createTestingPinia } from "@pinia/testing";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import {
    getPersistentKey,
    getStoredProgressDataByKey,
    type MonitoringRequest,
} from "@/composables/persistentProgressMonitor";
import type { ExportableItem } from "@/stores/exportToAnotherGalaxyStore";

import { useExportForAnotherGalaxy } from "./exportForAnotherGalaxy";

const PREPARE = "/api/histories/{history_id}/contents/{type}s/{id}/prepare_store_download";

const { server, http } = useServerMock();

let prepareUrls: string[] = [];
let prepareBodies: unknown[] = [];
let exporter: ReturnType<typeof useExportForAnotherGalaxy>;

beforeEach(() => {
    prepareUrls = [];
    prepareBodies = [];
    localStorage.clear();
    setActivePinia(createTestingPinia({ createSpy: vi.fn, stubActions: false }));
    exporter = useExportForAnotherGalaxy();
});

// Exports are followed to their end on their own, so stop them before the next test.
afterEach(() => {
    exporter.stopAll();
    vi.restoreAllMocks();
});

function dataset(contentId: string): ExportableItem {
    return { historyId: "h1", contentType: "dataset", contentId, contentName: `${contentId}.bed` };
}

function collection(contentId: string): ExportableItem {
    return { historyId: "h1", contentType: "dataset_collection", contentId, contentName: `${contentId} list` };
}

function recentExportRecord(contentId: string, type = "dataset") {
    const request = {
        source: "history-content-export",
        action: "export",
        taskType: "short_term_storage",
        object: { id: contentId, type },
    } as MonitoringRequest;
    return getStoredProgressDataByKey(getPersistentKey(request));
}

/** Each prepare request gets its own storage request and task, named after the item. */
function exportsEndIn(state: string, reason = "") {
    server.use(
        http.post(PREPARE, async ({ params, request, response }) => {
            prepareUrls.push(request.url);
            prepareBodies.push(await request.json());
            const type = request.url.includes("/dataset_collections/") ? "dataset_collection" : "dataset";
            const id = `${type}-${params.id}-${prepareUrls.length}`;
            return response(200).json({ storage_request_id: `req-${id}`, task: { id: `task-${id}` } } as never);
        }),
        http.get("/api/tasks/{task_id}/state", ({ response }) => response(200).json(state as never)),
        http.get("/api/tasks/{task_id}/result", ({ response }) =>
            response(200).json({ state, result: reason } as never),
        ),
    );
}

describe("useExportForAnotherGalaxy", () => {
    it("starts, follows and finishes an export with a link to its storage", async () => {
        exportsEndIn("SUCCESS");
        const state = exporter.start(dataset("d1"));
        expect(state.value.status).toBe("starting");
        await vi.waitFor(() => expect(state.value.status).toBe("ready"));
        expect(state.value.link).toMatch(/^https?:\/\/.*\/api\/short_term_storage\/req-dataset-d1-1$/);
        expect(state.value.error).toBeUndefined();
        expect(prepareUrls).toEqual([
            expect.stringContaining("/histories/h1/contents/datasets/d1/prepare_store_download"),
        ]);
        expect(prepareBodies[0]).toEqual({
            model_store_format: "tar.gz",
            include_files: true,
            include_deleted: false,
            include_hidden: false,
        });
        await vi.waitFor(() => expect(recentExportRecord("d1")).toMatchObject({ isFinal: true, taskStatus: "READY" }));
    });

    it("shows the export as running while its task is pending", async () => {
        exportsEndIn("PENDING");
        const state = exporter.start(dataset("d1"));
        await vi.waitFor(() => expect(state.value.status).toBe("running"));
        expect(state.value.link).toBeUndefined();
    });

    it("exports several items side by side, keeping datasets and collections with the same id apart", async () => {
        exportsEndIn("SUCCESS");
        const first = exporter.start(dataset("x1"));
        const second = exporter.start(collection("x1"));
        const third = exporter.start(dataset("d2"));
        await vi.waitFor(() =>
            expect([first.value.status, second.value.status, third.value.status]).toEqual(["ready", "ready", "ready"]),
        );
        expect(prepareUrls).toHaveLength(3);
        expect(new Set([first.value.link, second.value.link, third.value.link]).size).toBe(3);
        expect(second.value.link).toContain("req-dataset_collection-x1");
        await vi.waitFor(() => expect(recentExportRecord("x1", "collection")).toMatchObject({ taskStatus: "READY" }));
    });

    it("reuses a recent export of the same item", async () => {
        exportsEndIn("SUCCESS");
        const first = exporter.start(dataset("d1"));
        await vi.waitFor(() => expect(first.value.status).toBe("ready"));
        const again = exporter.start(dataset("d1"));
        expect(again.value).toEqual(first.value);
        expect(prepareUrls).toHaveLength(1);
    });

    it("starts a new export once the old one is an hour old", async () => {
        exportsEndIn("SUCCESS");
        const now = Date.now();
        const first = exporter.start(dataset("d1"));
        await vi.waitFor(() => expect(first.value.status).toBe("ready"));
        vi.spyOn(Date, "now").mockReturnValue(now + 61 * 60 * 1000);
        const again = exporter.start(dataset("d1"));
        await vi.waitFor(() => expect(prepareUrls).toHaveLength(2));
        await vi.waitFor(() => expect(again.value.link).toContain("req-dataset-d1-2"));
    });

    it("does not start a second export while the first request has not come back", async () => {
        let answer: () => void = () => {};
        const answered = new Promise<void>((resolve) => (answer = resolve));
        exportsEndIn("SUCCESS");
        server.use(
            http.post(PREPARE, async ({ request, response }) => {
                prepareUrls.push(request.url);
                await answered;
                return response(200).json({ storage_request_id: "req1", task: { id: "task1" } } as never);
            }),
        );
        const first = exporter.start(dataset("d1"));
        await vi.waitFor(() => expect(prepareUrls).toHaveLength(1));
        const again = exporter.start(dataset("d1"));
        expect(again.value.status).toBe("starting");
        answer();
        await vi.waitFor(() => expect(first.value.status).toBe("ready"));
        expect(again.value.status).toBe("ready");
        expect(prepareUrls).toHaveLength(1);
    });

    it("reports a refused export request, and tries again on the next start", async () => {
        server.use(
            http.post(PREPARE, ({ request, response }) => {
                prepareUrls.push(request.url);
                return response("4XX").json(
                    { err_msg: "You may not export this dataset", err_code: 403001 },
                    {
                        status: 403,
                    },
                );
            }),
        );
        const state = exporter.start(dataset("d1"));
        await vi.waitFor(() => expect(state.value.status).toBe("failed"));
        expect(state.value.error).toContain("You may not export this dataset");
        exportsEndIn("SUCCESS");
        const retry = exporter.start(dataset("d1"));
        expect(retry.value).toEqual({ status: "starting" });
        await vi.waitFor(() => expect(retry.value.status).toBe("ready"));
        expect(prepareUrls).toHaveLength(2);
    });

    it("reports why the export task failed, records it, and starts afresh on the next start", async () => {
        exportsEndIn("FAILURE", "Unknown error: the file is missing");
        const state = exporter.start(dataset("d1"));
        await vi.waitFor(() =>
            expect(state.value).toEqual({ status: "failed", error: "Unknown error: the file is missing" }),
        );
        await vi.waitFor(() =>
            expect(recentExportRecord("d1")).toMatchObject({
                isFinal: true,
                taskStatus: "FAILURE",
                failureReason: "Unknown error: the file is missing",
            }),
        );
        exportsEndIn("SUCCESS");
        const retry = exporter.start(dataset("d1"));
        await vi.waitFor(() => expect(retry.value.status).toBe("ready"));
        expect(prepareUrls).toHaveLength(2);
    });

    it("gives a generic reason when a failed task has none", async () => {
        exportsEndIn("FAILURE", "");
        const state = exporter.start(dataset("d1"));
        await vi.waitFor(() => expect(state.value).toEqual({ status: "failed", error: "The export failed." }));
    });

    it("reports a task state it cannot fetch, and asks again on the next start without a new export", async () => {
        exportsEndIn("SUCCESS");
        server.use(
            http.get("/api/tasks/{task_id}/state", ({ response }) =>
                response("5XX").json({ err_msg: "Server unavailable", err_code: 500001 }, { status: 500 }),
            ),
        );
        const state = exporter.start(dataset("d1"));
        await vi.waitFor(() =>
            expect(state.value).toEqual({
                status: "failed",
                error: "Galaxy could not say how the export is going. Please try again later.",
            }),
        );
        exportsEndIn("SUCCESS");
        exporter.start(dataset("d1"));
        await vi.waitFor(() => expect(state.value.status).toBe("ready"));
        expect(prepareUrls).toHaveLength(1);
    });

    it("shares exports between every user of the composable", async () => {
        exportsEndIn("SUCCESS");
        const state = exporter.start(dataset("d1"));
        await vi.waitFor(() => expect(state.value.status).toBe("ready"));
        const other = useExportForAnotherGalaxy();
        expect(other.stateOf(dataset("d1"))).toEqual(state.value);
        expect(other.stateOf(dataset("d2"))).toBeUndefined();
        other.start(dataset("d1"));
        expect(prepareUrls).toHaveLength(1);
    });
});
