import { createTestingPinia } from "@pinia/testing";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { type HistorySummary } from "@/api";
import { mockFetcher } from "@/api/schema/__mocks__";
import { useHistoryStore } from "@/stores/historyStore";

import HistoryArchiveWizard from "./HistoryArchiveWizard.vue";

jest.mock("@/api/schema");

jest.mock("@/composables/config", () => ({
    useConfig: jest.fn(() => ({
        config: {
            value: {
                enable_celery_tasks: true,
            },
        },
    })),
}));

const localVue = getLocalVue(true);

const TEST_HISTORY_ID = "test-history-id";
const TEST_HISTORY = {
    id: TEST_HISTORY_ID,
    name: "fake-history-name",
    archived: false,
};

const ARCHIVED_TEST_HISTORY = {
    ...TEST_HISTORY,
    archived: true,
};

const REMOTE_FILES_API_ENDPOINT = new RegExp("/api/remote_files/plugins");

async function mountComponentWithHistory(history?: HistorySummary) {
    const pinia = createTestingPinia({ stubActions: false });
    setActivePinia(pinia);
    const historyStore = useHistoryStore(pinia);

    // the mocking method described in the pinia docs does not work in vue2
    // this is a work-around
    jest.spyOn(historyStore, "getHistoryById").mockImplementation((_history_id: string) => history as HistorySummary);

    const wrapper = shallowMount(HistoryArchiveWizard, {
        propsData: { historyId: TEST_HISTORY_ID },
        localVue,
        pinia,
    });
    await flushPromises();
    return wrapper;
}

describe("HistoryArchiveWizard.vue", () => {
    beforeEach(async () => {
        mockFetcher.path(REMOTE_FILES_API_ENDPOINT).method("get").mock({ data: [] });
    });

    it("should render the history name in the header", async () => {
        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const header = wrapper.find("h1");
        expect(header.text()).toContain(TEST_HISTORY.name);
    });

    it("should render only the simple archival mode when no writeable file sources are available", async () => {
        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const optionTabs = wrapper.findAll(".archival-option-tabs");
        expect(optionTabs.exists()).toBe(false);
    });

    it("should render both archival modes when writeable file sources and celery tasks are available", async () => {
        mockFetcher
            .path(REMOTE_FILES_API_ENDPOINT)
            .method("get")
            .mock({
                data: [
                    {
                        id: "test-posix-source",
                        type: "posix",
                        uri_root: "gxfiles://test-posix-source",
                        label: "TestSource",
                        doc: "For testing",
                        writable: true,
                        requires_roles: undefined,
                        requires_groups: undefined,
                    },
                ],
            });
        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const optionTabs = wrapper.findAll(".archival-option-tabs");
        expect(optionTabs.exists()).toBe(true);

        const keepStorageOption = wrapper.find("#keep-storage-tab");
        expect(keepStorageOption.exists()).toBe(true);

        const freeStorageOption = wrapper.find("#free-storage-tab");
        expect(freeStorageOption.exists()).toBe(true);
    });

    it("should display a success alert when the history is archived instead of the archival options", async () => {
        const wrapper = await mountComponentWithHistory(ARCHIVED_TEST_HISTORY as HistorySummary);

        const optionTabs = wrapper.findAll(".archival-option-tabs");
        expect(optionTabs.exists()).toBe(false);

        const successMessage = wrapper.find("#history-archived-alert");
        expect(successMessage.exists()).toBe(true);
    });
});
