import { createTestingPinia } from "@pinia/testing";
import { getFakeHistorySummary } from "@tests/test-data";
import { getFakeFileSource } from "@tests/test-data/fileSources";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { HistorySummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { useHistoryStore } from "@/stores/historyStore";

import HistoryArchiveWizard from "./HistoryArchiveWizard.vue";

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({
        config: {
            value: {
                enable_celery_tasks: true,
            },
        },
    })),
}));

enableAutoUnmount(afterEach);

const { server, http } = useServerMock();
const TEST_HISTORY_ID = "test-history-id";

async function mountComponentWithHistory(history: HistorySummary) {
    const localVue = getLocalVue(true);
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    const historyStore = useHistoryStore(pinia);

    historyStore.setHistories([history]);

    const wrapper = shallowMount(HistoryArchiveWizard as object, {
        props: { historyId: TEST_HISTORY_ID },
        global: withPlugins(localVue, pinia),
    });
    await flushPromises();
    return wrapper;
}

describe("HistoryArchiveWizard.vue", () => {
    beforeEach(() => {
        server.use(
            http.get("/api/remote_files/plugins", ({ response }) => {
                return response(200).json([]);
            }),
        );
    });

    it("shows simple archival without tabs when no writable file sources are available", async () => {
        const wrapper = await mountComponentWithHistory(getFakeHistorySummary({ id: TEST_HISTORY_ID }));

        const optionTabs = wrapper.findAll(".archival-option-tabs");
        expect(optionTabs).toHaveLength(0);
        expect(wrapper.findComponent({ name: "HistoryArchiveSimple" }).exists()).toBe(true);
    });

    it("shows both archival modes when writable file sources and Celery tasks are available", async () => {
        server.use(
            http.get("/api/remote_files/plugins", ({ response }) => {
                return response(200).json([
                    getFakeFileSource({
                        id: "test-posix-source",
                        label: "TestSource",
                        doc: "For testing",
                    }),
                ]);
            }),
        );

        const wrapper = await mountComponentWithHistory(getFakeHistorySummary({ id: TEST_HISTORY_ID }));

        const optionTabs = wrapper.findAll(".archival-option-tabs");
        expect(optionTabs.length).toBeGreaterThan(0);

        const keepStorageOption = wrapper.find("#keep-storage-tab");
        expect(keepStorageOption.exists()).toBe(true);

        const freeStorageOption = wrapper.find("#free-storage-tab");
        expect(freeStorageOption.exists()).toBe(true);
    });

    it("shows an archived history alert instead of archival options", async () => {
        const wrapper = await mountComponentWithHistory(getFakeHistorySummary({ id: TEST_HISTORY_ID, archived: true }));

        const optionTabs = wrapper.findAll(".archival-option-tabs");
        expect(optionTabs.length).toBe(0);

        const successMessage = wrapper.find("#history-archived-alert");
        expect(successMessage.exists()).toBe(true);
    });
});
