import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { BFormCheckbox } from "bootstrap-vue";
import HistoryArchiveExportSelector from "./HistoryArchiveExportSelector.vue";
import type { HistorySummary } from "@/stores/historyStore";
import { mockFetcher } from "@/schema/__mocks__";
import {
    FAILED_FILE_SOURCE_STORE_RESPONSE,
    FILE_SOURCE_STORE_RESPONSE,
    IN_PROGRESS_FILE_SOURCE_STORE_RESPONSE,
    RECENT_FILE_SOURCE_STORE_RESPONSE,
    RECENT_STS_DOWNLOAD_RESPONSE,
} from "@/components/Common/models/testData/exportData";

jest.mock("@/schema");

const localVue = getLocalVue(true);

const TEST_HISTORY_ID = "test-history-id";
const TEST_HISTORY = {
    id: TEST_HISTORY_ID,
    name: "fake-history-name",
    archived: false,
};

const GET_EXPORTS_API_ENDPOINT = "/api/histories/{history_id}/exports";

const EXPORT_RECORD_BTN = "#create-export-record-btn";
const ARCHIVE_HISTORY_BTN = "#archive-history-btn";
const CONFIRM_DELETE_CHECKBOX = "[type='checkbox']";

async function mountComponentWithHistory(history: HistorySummary) {
    const wrapper = shallowMount(HistoryArchiveExportSelector, {
        propsData: { history },
        localVue,
        stubs: {
            // Stub with the real component to be able to use setChecked
            BFormCheckbox,
        },
    });
    await flushPromises();
    return wrapper;
}

describe("HistoryArchiveExportSelector.vue", () => {
    let axiosMock: MockAdapter;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("should display a button to create an export record if there is no up to date export record", async () => {
        mockFetcher.path(GET_EXPORTS_API_ENDPOINT).method("get").mock({ data: [] });

        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const createExportButton = wrapper.find(EXPORT_RECORD_BTN);
        expect(createExportButton.exists()).toBe(true);
    });

    it("should display a button to create an export record if the most recent export record is not permanent", async () => {
        mockFetcher
            .path(GET_EXPORTS_API_ENDPOINT)
            .method("get")
            .mock({ data: [RECENT_STS_DOWNLOAD_RESPONSE] });

        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const createExportButton = wrapper.find(EXPORT_RECORD_BTN);
        expect(createExportButton.exists()).toBe(true);
    });

    it("should display a button to create an export record if there are permanent export records but none are up to date", async () => {
        mockFetcher
            .path(GET_EXPORTS_API_ENDPOINT)
            .method("get")
            .mock({ data: [FILE_SOURCE_STORE_RESPONSE, FAILED_FILE_SOURCE_STORE_RESPONSE] });

        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const createExportButton = wrapper.find(EXPORT_RECORD_BTN);
        expect(createExportButton.exists()).toBe(true);
    });

    it("should not display a button to create an export record if there is an up to date export record", async () => {
        mockFetcher
            .path(GET_EXPORTS_API_ENDPOINT)
            .method("get")
            .mock({ data: [RECENT_FILE_SOURCE_STORE_RESPONSE] });

        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const createExportButton = wrapper.find(EXPORT_RECORD_BTN);
        expect(createExportButton.exists()).toBe(false);
    });

    it("should not display a button to create an export record if a record is being created", async () => {
        mockFetcher
            .path(GET_EXPORTS_API_ENDPOINT)
            .method("get")
            .mock({ data: [IN_PROGRESS_FILE_SOURCE_STORE_RESPONSE] });

        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const createExportButton = wrapper.find(EXPORT_RECORD_BTN);
        expect(createExportButton.exists()).toBe(false);
    });

    it("should disable the Archive button if there is no up to date export record", async () => {
        mockFetcher.path(GET_EXPORTS_API_ENDPOINT).method("get").mock({ data: [] });

        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const archiveButton = wrapper.find(ARCHIVE_HISTORY_BTN);
        expect(archiveButton.attributes("disabled")).toBeTruthy();
    });

    it("should disable the Archive button if the confirm delete checkbox is not checked", async () => {
        mockFetcher
            .path(GET_EXPORTS_API_ENDPOINT)
            .method("get")
            .mock({ data: [RECENT_FILE_SOURCE_STORE_RESPONSE] });

        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const confirmDeleteCheckbox = wrapper.find(CONFIRM_DELETE_CHECKBOX);
        await confirmDeleteCheckbox.setChecked(false);
        expect((confirmDeleteCheckbox.element as HTMLInputElement).checked).toBeFalsy();

        const archiveButton = wrapper.find(ARCHIVE_HISTORY_BTN);
        expect(archiveButton.attributes("disabled")).toBeTruthy();
    });

    it("should enable the Archive button if there is an up to date export record and the confirm delete checkbox is checked", async () => {
        mockFetcher
            .path(GET_EXPORTS_API_ENDPOINT)
            .method("get")
            .mock({ data: [RECENT_FILE_SOURCE_STORE_RESPONSE] });

        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const confirmDeleteCheckbox = wrapper.find(CONFIRM_DELETE_CHECKBOX);
        await confirmDeleteCheckbox.setChecked(true);
        expect((confirmDeleteCheckbox.element as HTMLInputElement).checked).toBeTruthy();

        const archiveButton = wrapper.find(ARCHIVE_HISTORY_BTN);
        expect(archiveButton.attributes("disabled")).toBeFalsy();
    });
});
