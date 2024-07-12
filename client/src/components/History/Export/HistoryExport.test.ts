import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { shallowMount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";

import type { HistorySummary } from "@/api";
import { fetchHistoryExportRecords } from "@/api/histories.export";
import type { FilesSourcePlugin } from "@/api/remoteFiles";
import { mockFetcher } from "@/api/schema/__mocks__";
import {
    EXPIRED_STS_DOWNLOAD_RECORD,
    FILE_SOURCE_STORE_RECORD,
    RECENT_STS_DOWNLOAD_RECORD,
} from "@/components/Common/models/testData/exportData";

import HistoryExport from "./HistoryExport.vue";

const localVue = getLocalVue(true);

jest.mock("@/api/schema");
jest.mock("@/api/histories.export");
const mockFetchExportRecords = fetchHistoryExportRecords as jest.MockedFunction<typeof fetchHistoryExportRecords>;
mockFetchExportRecords.mockResolvedValue([]);

const FAKE_HISTORY_ID = "fake-history-id";
const FAKE_HISTORY_URL = `/api/histories/${FAKE_HISTORY_ID}`;
const FAKE_HISTORY: HistorySummary = {
    id: FAKE_HISTORY_ID,
    name: "fake-history-name",
    annotation: "fake-history-annotation",
    archived: false,
    deleted: false,
    purged: false,
    published: false,
    model_class: "History",
    tags: [],
    count: 0,
    update_time: "2021-09-01T00:00:00.000Z",
    url: FAKE_HISTORY_URL,
};

const REMOTE_FILES_API_ENDPOINT = new RegExp("/api/remote_files/plugins");

const REMOTE_FILES_API_RESPONSE: FilesSourcePlugin[] = [
    {
        id: "test-posix-source",
        type: "posix",
        label: "TestSource",
        doc: "For testing",
        writable: true,
        browsable: true,
        requires_roles: undefined,
        requires_groups: undefined,
    },
];

async function mountHistoryExport() {
    const pinia = createTestingPinia({ stubActions: false });
    setActivePinia(pinia);

    const wrapper = shallowMount(HistoryExport as object, {
        propsData: { historyId: FAKE_HISTORY_ID },
        localVue,
        pinia,
    });
    await flushPromises();
    return wrapper;
}

describe("HistoryExport.vue", () => {
    let axiosMock: MockAdapter;

    beforeEach(async () => {
        mockFetcher.path(REMOTE_FILES_API_ENDPOINT).method("get").mock({ data: [] });
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet(FAKE_HISTORY_URL).reply(200, FAKE_HISTORY);
    });

    it("should render the history name", async () => {
        const wrapper = await mountHistoryExport();

        expect(wrapper.find("#history-name").text()).toBe(FAKE_HISTORY.name);
    });

    it("should render export options", async () => {
        const wrapper = await mountHistoryExport();

        expect(wrapper.find("#history-export-options").exists()).toBe(true);
    });

    it("should display a message indicating there are no exports where there are none", async () => {
        const wrapper = await mountHistoryExport();

        expect(wrapper.find("#no-export-records-alert").exists()).toBe(true);
    });

    it("should render previous records when there is more than one record", async () => {
        mockFetchExportRecords.mockResolvedValue([
            RECENT_STS_DOWNLOAD_RECORD,
            FILE_SOURCE_STORE_RECORD,
            EXPIRED_STS_DOWNLOAD_RECORD,
        ]);
        const wrapper = await mountHistoryExport();

        expect(wrapper.find("#previous-export-records").exists()).toBe(true);
    });

    it("should not render previous records when there is one or less records", async () => {
        mockFetchExportRecords.mockResolvedValue([RECENT_STS_DOWNLOAD_RECORD]);
        const wrapper = await mountHistoryExport();

        expect(wrapper.find("#previous-export-records").exists()).toBe(false);
    });

    it("should display file sources tab if there are available", async () => {
        mockFetcher.path(REMOTE_FILES_API_ENDPOINT).method("get").mock({ data: REMOTE_FILES_API_RESPONSE });
        const wrapper = await mountHistoryExport();

        expect(wrapper.find("#direct-download-tab").exists()).toBe(true);
        expect(wrapper.find("#file-source-tab").exists()).toBe(true);
    });

    it("should not display file sources tab if there are no file sources available", async () => {
        const wrapper = await mountHistoryExport();

        expect(wrapper.find("#direct-download-tab").exists()).toBe(true);
        expect(wrapper.find("#file-source-tab").exists()).toBe(false);
    });

    it("should display the ZENODO tab if the Zenodo plugin is available", async () => {
        const zenodoPlugin: FilesSourcePlugin = {
            id: "zenodo",
            type: "rdm",
            label: "Zenodo",
            doc: "For testing",
            writable: true,
            browsable: true,
        };
        mockFetcher
            .path(REMOTE_FILES_API_ENDPOINT)
            .method("get")
            .mock({ data: [zenodoPlugin] });
        const wrapper = await mountHistoryExport();

        expect(wrapper.find("#zenodo-file-source-tab").exists()).toBe(true);
    });

    it("should not display a fatal error alert if the history is found and loaded", async () => {
        const wrapper = await mountHistoryExport();

        expect(wrapper.find("#fatal-error-alert").exists()).toBe(false);

        expect(wrapper.find("#history-name").exists()).toBe(true);
        expect(wrapper.find("#history-export-options").exists()).toBe(true);
        expect(wrapper.find("#direct-download-tab").exists()).toBe(true);
    });

    it("should not render the UI and display a fatal error message if the history cannot be found or loaded", async () => {
        axiosMock.onGet(FAKE_HISTORY_URL).reply(404);
        const wrapper = await mountHistoryExport();

        expect(wrapper.find("#fatal-error-alert").exists()).toBe(true);

        expect(wrapper.find("#history-name").exists()).toBe(false);
        expect(wrapper.find("#history-export-options").exists()).toBe(false);
        expect(wrapper.find("#direct-download-tab").exists()).toBe(false);
    });
});
