import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import {
    getPersistentKey,
    getStoredProgressDataByKey,
    type MonitoringRequest,
} from "@/composables/persistentProgressMonitor";
import { type ExportableItem, useExportToAnotherGalaxyStore } from "@/stores/exportToAnotherGalaxyStore";

import ExportToAnotherGalaxyDialog from "./ExportToAnotherGalaxyDialog.vue";

const PREPARE = "/api/histories/{history_id}/contents/{type}s/{id}/prepare_store_download";

const { server, http } = useServerMock();

let exportUrls: string[] = [];

beforeEach(() => {
    exportUrls = [];
    localStorage.clear();
});

function recentExportRecord(contentId: string) {
    const request = {
        source: "history-content-export",
        action: "export",
        taskType: "short_term_storage",
        object: { id: contentId, type: "dataset" },
    } as MonitoringRequest;
    return getStoredProgressDataByKey(getPersistentKey(request));
}

function exportEndsIn(state: string, reason = "") {
    server.use(
        http.post(PREPARE, ({ request, response }) => {
            exportUrls.push(request.url);
            return response(200).json({ storage_request_id: "req1", task: { id: "task1" } } as never);
        }),
        http.get("/api/tasks/{task_id}/state", ({ response }) => response(200).json(state as never)),
        http.get("/api/tasks/{task_id}/result", ({ response }) =>
            response(200).json({ state, result: reason } as never),
        ),
    );
}

function dataset(contentId: string): ExportableItem {
    return { historyId: "h1", contentType: "dataset", contentId, contentName: "reads.bed" };
}

function mountDialog() {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    const wrapper = mount(ExportToAnotherGalaxyDialog as object, {
        global: withPlugins(getLocalVue(), pinia),
    });
    return { wrapper, store: useExportToAnotherGalaxyStore(pinia) };
}

const linkInput = (wrapper: VueWrapper) => wrapper.find('[data-description="galaxy export link"]');

describe("ExportToAnotherGalaxyDialog", () => {
    it("shows the link once the export task has finished", async () => {
        exportEndsIn("SUCCESS");
        const { wrapper, store } = mountDialog();
        store.open(dataset("d1"));
        await vi.waitFor(() => expect(linkInput(wrapper).exists()).toBe(true));
        expect((linkInput(wrapper).element as HTMLInputElement).value).toMatch(
            /^https?:\/\/.*\/api\/short_term_storage\/req1$/,
        );
        expect(exportUrls[0]).toContain("/contents/datasets/d1/prepare_store_download");
    });

    it("shows why the export failed instead of a link", async () => {
        exportEndsIn("FAILURE", "Unknown error: the file is missing");
        const { wrapper, store } = mountDialog();
        store.open(dataset("d1"));
        await vi.waitFor(() => expect(wrapper.text()).toContain("Unknown error: the file is missing"));
        expect(linkInput(wrapper).exists()).toBe(false);
    });

    it("reuses the export when the same item is opened again", async () => {
        exportEndsIn("SUCCESS");
        const { wrapper, store } = mountDialog();
        store.open(dataset("d1"));
        await vi.waitFor(() => expect(linkInput(wrapper).exists()).toBe(true));
        store.close();
        store.open(dataset("d1"));
        await vi.waitFor(() => expect(linkInput(wrapper).exists()).toBe(true));
        expect(exportUrls).toHaveLength(1);
    });

    it("starts a fresh export after a failed one, without the old error", async () => {
        exportEndsIn("FAILURE", "Unknown error: the file is missing");
        const { wrapper, store } = mountDialog();
        store.open(dataset("d1"));
        await vi.waitFor(() => expect(wrapper.text()).toContain("Unknown error: the file is missing"));
        let answerRetry = () => {};
        server.use(
            http.post(PREPARE, async ({ request, response }) => {
                exportUrls.push(request.url);
                await new Promise<void>((resolve) => (answerRetry = resolve));
                return response(200).json({ storage_request_id: "req2", task: { id: "task2" } } as never);
            }),
        );
        store.close();
        store.open(dataset("d1"));
        await vi.waitFor(() => expect(exportUrls).toHaveLength(2));
        expect(wrapper.text()).not.toContain("Unknown error");
        answerRetry();
    });

    it("records the finished export for Recent Exports", async () => {
        exportEndsIn("SUCCESS");
        const { wrapper, store } = mountDialog();
        store.open(dataset("d1"));
        await vi.waitFor(() => expect(linkInput(wrapper).exists()).toBe(true));
        await vi.waitFor(() => expect(recentExportRecord("d1")).toMatchObject({ isFinal: true, taskStatus: "READY" }));
    });

    it("records a failed export as failed rather than ready", async () => {
        exportEndsIn("FAILURE", "Unknown error: the file is missing");
        const { wrapper, store } = mountDialog();
        store.open(dataset("d1"));
        await vi.waitFor(() => expect(wrapper.text()).toContain("Unknown error: the file is missing"));
        await vi.waitFor(() =>
            expect(recentExportRecord("d1")).toMatchObject({
                isFinal: true,
                failureReason: "Unknown error: the file is missing",
            }),
        );
        expect(recentExportRecord("d1")?.taskStatus).not.toBe("READY");
    });

    it("exports a collection and says so", async () => {
        exportEndsIn("SUCCESS");
        const { wrapper, store } = mountDialog();
        store.open({ historyId: "h1", contentType: "dataset_collection", contentId: "c1", contentName: "peaks" });
        await vi.waitFor(() => expect(linkInput(wrapper).exists()).toBe(true));
        expect(exportUrls[0]).toContain("/contents/dataset_collections/c1/prepare_store_download");
        expect(wrapper.text()).toContain("download this collection");
    });
});
