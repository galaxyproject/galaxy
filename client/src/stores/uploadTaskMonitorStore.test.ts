import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import type { NewUploadItem } from "@/composables/upload/uploadItemTypes";

import { COULD_NOT_CHECK_IMPORT, INTERRUPTED_IMPORT, useUploadTaskMonitorStore } from "./uploadTaskMonitorStore";

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

    it("fails an import that a previous page left without a task", () => {
        const id = uploadState.addUploadItem(linkItem());
        const other = uploadState.addUploadItem({
            ...linkItem(),
            uploadMode: "paste-content",
            content: "x",
        } as NewUploadItem);
        useUploadTaskMonitorStore();
        expect(itemOf(id)).toMatchObject({ status: "error", error: INTERRUPTED_IMPORT });
        expect(itemOf(other).status).toBe("queued");
    });
});
