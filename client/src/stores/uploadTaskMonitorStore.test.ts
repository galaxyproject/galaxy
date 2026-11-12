import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import type { useTaskMonitor } from "@/composables/taskMonitor";
import type { NewUploadItem, UploadItem } from "@/composables/upload/uploadItemTypes";

import {
    COULD_NOT_CHECK_IMPORT,
    INTERRUPTED_IMPORT,
    redactExportLinks,
    useUploadTaskMonitorStore,
} from "./uploadTaskMonitorStore";

const monitorOptions = vi.hoisted(() => ({ withoutExpiration: false }));

vi.mock("@/composables/taskMonitor", async (importOriginal) => {
    const actual = await importOriginal<{ useTaskMonitor: typeof useTaskMonitor }>();
    return {
        useTaskMonitor: (options?: Parameters<typeof useTaskMonitor>[0]) => {
            const monitor = actual.useTaskMonitor(options);
            return monitorOptions.withoutExpiration ? { ...monitor, expirationTime: undefined } : monitor;
        },
    };
});

const { server, http } = useServerMock();

function linkItem(name = "reads.bed"): NewUploadItem {
    return {
        uploadMode: "galaxy-link",
        name,
        sourceHost: "usegalaxy.eu",
        size: 0,
        targetHistoryId: "hist_1",
        dbkey: "?",
        extension: "auto",
        spaceToTab: false,
        toPosixLines: false,
        autoDecompress: false,
        deferred: false,
    };
}

function tasksEndIn(state: string, reason = "") {
    const checked: string[] = [];
    server.use(
        http.get("/api/tasks/{task_id}/state", ({ params, response }) => {
            checked.push(String(params.task_id));
            return response(200).json(state as never);
        }),
        http.get("/api/tasks/{task_id}/result", ({ response }) =>
            response(200).json({ state, result: reason } as never),
        ),
    );
    return checked;
}

const DAY_MS = 24 * 60 * 60 * 1000;

/** An item as an earlier page stored it, created before this page loaded. */
function storedItem(overrides: Record<string, unknown>): UploadItem {
    return {
        ...linkItem(),
        datasetIds: [],
        createdAt: Date.now() - 60 * 1000,
        progress: 100,
        ...overrides,
    } as unknown as UploadItem;
}

let uploadState: ReturnType<typeof useUploadState>;

function itemOf(id: string) {
    return uploadState.activeItems.value.find((item) => item.id === id)!;
}

beforeEach(() => {
    setActivePinia(createPinia());
    uploadState = useUploadState();
    uploadState.clearAll();
});

afterEach(() => {
    uploadState.clearAll();
    useUploadTaskMonitorStore().$dispose();
    vi.useRealTimers();
    monitorOptions.withoutExpiration = false;
});

describe("useUploadTaskMonitorStore", () => {
    it("follows an import started before the page was loaded until its task succeeds", async () => {
        const checked = tasksEndIn("SUCCESS");
        const id = uploadState.addUploadItem(linkItem());
        uploadState.markTaskStarted(id, "task1");
        useUploadTaskMonitorStore();
        await vi.waitFor(() => expect(itemOf(id).status).toBe("completed"));
        expect(checked).toEqual(["task1"]);
    });

    it("starts following an import once its task has started", async () => {
        tasksEndIn("SUCCESS");
        useUploadTaskMonitorStore();
        const id = uploadState.addUploadItem(linkItem());
        await vi.waitFor(() => expect(itemOf(id).status).toBe("queued"));
        uploadState.markTaskStarted(id, "task1");
        await vi.waitFor(() => expect(itemOf(id).status).toBe("completed"));
    });

    it("marks the item failed with the task's reason", async () => {
        tasksEndIn("FAILURE", "404 Not Found");
        useUploadTaskMonitorStore();
        const id = uploadState.addUploadItem(linkItem());
        uploadState.markTaskStarted(id, "task1");
        await vi.waitFor(() => expect(itemOf(id).status).toBe("error"));
        expect(itemOf(id).error).toContain("may have expired");
        expect(itemOf(id).error).toContain("404 Not Found");
    });

    it("says it could not check the import only after several failed checks in a row", async () => {
        vi.useFakeTimers({ shouldAdvanceTime: true });
        let checks = 0;
        server.use(
            http.get("/api/tasks/{task_id}/state", ({ response }) => {
                checks++;
                return response("5XX").json({ err_msg: "Bad Gateway", err_code: 502 }, { status: 502 });
            }),
        );
        useUploadTaskMonitorStore();
        const id = uploadState.addUploadItem(linkItem());
        uploadState.markTaskStarted(id, "task1");
        await vi.waitFor(() => expect(checks).toBe(1));
        await vi.advanceTimersByTimeAsync(3000);
        await vi.waitFor(() => expect(checks).toBe(2));
        expect(itemOf(id).status).toBe("processing");
        await vi.advanceTimersByTimeAsync(3000);
        await vi.waitFor(() => expect(itemOf(id).status).toBe("error"));
        expect(itemOf(id).error).toBe(COULD_NOT_CHECK_IMPORT);
    });

    it("fails an import that a previous page left without a task, once the user's upload state has loaded", async () => {
        useUploadTaskMonitorStore();
        const startingNow = uploadState.addUploadItem(linkItem());
        // The user's stored uploads arrive after the store exists, when the hashed user id is known.
        uploadState.activeItems.value = [
            ...uploadState.activeItems.value,
            storedItem({ id: "left", status: "queued", progress: 100 }),
            storedItem({ id: "pasted", uploadMode: "paste-content", content: "x", status: "queued" }),
        ];
        await vi.waitFor(() => expect(itemOf("left")).toMatchObject({ status: "error", error: INTERRUPTED_IMPORT }));
        expect(itemOf("pasted").status).toBe("queued");
        expect(itemOf(startingNow).status).toBe("queued");
    });

    it("stops following an import whose task is older than tasks are kept", async () => {
        const checked = tasksEndIn("PENDING");
        uploadState.activeItems.value = [
            storedItem({ id: "old", status: "processing", taskId: "task-old", createdAt: Date.now() - DAY_MS - 1000 }),
        ];
        useUploadTaskMonitorStore();
        await vi.waitFor(() => expect(itemOf("old")).toMatchObject({ status: "error", error: COULD_NOT_CHECK_IMPORT }));
        expect(checked).toEqual([]);
    });

    it("keeps following an old import when the monitor has no expiration time", async () => {
        monitorOptions.withoutExpiration = true;
        const checked = tasksEndIn("PENDING");
        uploadState.activeItems.value = [
            storedItem({ id: "old", status: "processing", taskId: "task-old", createdAt: Date.now() - 2 * DAY_MS }),
        ];
        useUploadTaskMonitorStore();
        await vi.waitFor(() => expect(checked).toEqual(["task-old"]));
        // A timer for an unknown expiration would fire at once, as browsers clamp an Infinity delay to 0.
        await new Promise((resolve) => setTimeout(resolve, 50));
        expect(itemOf("old").status).toBe("processing");
    });

    it("gives up on a task that is still pending when it expires", async () => {
        vi.useFakeTimers({ shouldAdvanceTime: true });
        const checked = tasksEndIn("PENDING");
        uploadState.activeItems.value = [
            storedItem({
                id: "late",
                status: "processing",
                taskId: "task-late",
                createdAt: Date.now() - DAY_MS + 5000,
            }),
        ];
        useUploadTaskMonitorStore();
        await vi.waitFor(() => expect(checked).toContain("task-late"));
        expect(itemOf("late").status).toBe("processing");
        await vi.advanceTimersByTimeAsync(6000);
        await vi.waitFor(() =>
            expect(itemOf("late")).toMatchObject({ status: "error", error: COULD_NOT_CHECK_IMPORT }),
        );
    });

    it("does not keep an export link that the task's failure reason repeats", async () => {
        const link = "https://usegalaxy.eu/galaxy/api/short_term_storage/0f8fad5b-d9cb-469f-a165-70867728950e";
        tasksEndIn("FAILURE", `404 Client Error: Not Found for url: ${link}`);
        useUploadTaskMonitorStore();
        const id = uploadState.addUploadItem(linkItem());
        uploadState.markTaskStarted(id, "task1");
        await vi.waitFor(() => expect(itemOf(id).status).toBe("error"));
        expect(itemOf(id).error).toContain("404 Client Error: Not Found for url: [export link]");
        expect(JSON.stringify(uploadState.activeItems.value)).not.toContain("0f8fad5b");
    });
});

describe("redactExportLinks", () => {
    it.each([
        [
            "Could not verify url 'https://a.example/api/short_term_storage/abc-1'.",
            "Could not verify url '[export link]'.",
        ],
        ["at http://localhost:8080/galaxy/api/short_term_storage/x?y=1 failed", "at [export link] failed"],
        [
            "HTTPSConnectionPool(host='usegalaxy.eu', port=443): Max retries exceeded with url: /api/short_term_storage/0f8fad5b-d9cb-469f-a165-70867728950e (Caused by NewConnectionError('timed out'))",
            "HTTPSConnectionPool(host='usegalaxy.eu', port=443): Max retries exceeded with url: [export link] (Caused by NewConnectionError('timed out'))",
        ],
        ["nothing to hide here", "nothing to hide here"],
    ])("hides the links in %j", (text, expected) => {
        expect(redactExportLinks(text)).toBe(expected);
    });
});
