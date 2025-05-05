import { shallowMount } from "@vue/test-utils";
import { BFormCheckbox } from "bootstrap-vue";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { type HistorySummary, type ObjectExportTaskResponse } from "@/api";
import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import {
    FAILED_FILE_SOURCE_STORE_RESPONSE,
    FILE_SOURCE_STORE_RESPONSE,
    IN_PROGRESS_FILE_SOURCE_STORE_RESPONSE,
    RECENT_FILE_SOURCE_STORE_RESPONSE,
    RECENT_STS_DOWNLOAD_RESPONSE,
} from "@/components/Common/models/testData/exportData";

import HistoryArchiveExportSelector from "./HistoryArchiveExportSelector.vue";

const localVue = getLocalVue(true);

const TEST_HISTORY_ID = "test-history-id";
const TEST_HISTORY = {
    id: TEST_HISTORY_ID,
    name: "fake-history-name",
    archived: false,
};

const EXPORT_RECORD_BTN = "#create-export-record-btn";
const ARCHIVE_HISTORY_BTN = "#archive-history-btn";
const CONFIRM_DELETE_CHECKBOX = "[type='checkbox']";

async function mountComponentWithHistory(history: HistorySummary) {
    const wrapper = shallowMount(HistoryArchiveExportSelector as object, {
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

const { server, http } = useServerMock();

function mockGetExportsApiResponse(taskExportResponse: ObjectExportTaskResponse[]) {
    server.use(
        http.get("/api/histories/{history_id}/exports", ({ response }) => {
            // We need to use the untyped version of the response here because the typed version does not support the
            // content-type "application/vnd.galaxy.task.export+json" that is returned by the server.
            return response.untyped(
                HttpResponse.json(taskExportResponse, {
                    status: 200,
                    headers: { "Content-Type": "application/vnd.galaxy.task.export+json" },
                })
            );
        })
    );
}

describe("HistoryArchiveExportSelector.vue", () => {
    it("should display a button to create an export record if there is no up to date export record", async () => {
        mockGetExportsApiResponse([]);

        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const createExportButton = wrapper.find(EXPORT_RECORD_BTN);
        expect(createExportButton.exists()).toBe(true);
    });

    it("should display a button to create an export record if the most recent export record is not permanent", async () => {
        mockGetExportsApiResponse([RECENT_STS_DOWNLOAD_RESPONSE]);

        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const createExportButton = wrapper.find(EXPORT_RECORD_BTN);
        expect(createExportButton.exists()).toBe(true);
    });

    it("should display a button to create an export record if there are permanent export records but none are up to date", async () => {
        mockGetExportsApiResponse([FILE_SOURCE_STORE_RESPONSE, FAILED_FILE_SOURCE_STORE_RESPONSE]);

        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const createExportButton = wrapper.find(EXPORT_RECORD_BTN);
        expect(createExportButton.exists()).toBe(true);
    });

    it("should not display a button to create an export record if there is an up to date export record", async () => {
        mockGetExportsApiResponse([RECENT_FILE_SOURCE_STORE_RESPONSE]);

        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const createExportButton = wrapper.find(EXPORT_RECORD_BTN);
        expect(createExportButton.exists()).toBe(false);
    });

    it("should not display a button to create an export record if a record is being created", async () => {
        mockGetExportsApiResponse([IN_PROGRESS_FILE_SOURCE_STORE_RESPONSE]);
        server.use(
            http.get("/api/tasks/{task_id}/state", ({ response }) => {
                return response(200).json("PENDING");
            })
        );

        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const createExportButton = wrapper.find(EXPORT_RECORD_BTN);
        expect(createExportButton.exists()).toBe(false);
    });

    it("should disable the Archive button if there is no up to date export record", async () => {
        mockGetExportsApiResponse([]);

        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const archiveButton = wrapper.find(ARCHIVE_HISTORY_BTN);
        expect(archiveButton.attributes("disabled")).toBeTruthy();
    });

    it("should disable the Archive button if the confirm delete checkbox is not checked", async () => {
        mockGetExportsApiResponse([RECENT_FILE_SOURCE_STORE_RESPONSE]);

        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const confirmDeleteCheckbox = wrapper.find(CONFIRM_DELETE_CHECKBOX);
        await confirmDeleteCheckbox.setChecked(false);
        expect((confirmDeleteCheckbox.element as HTMLInputElement).checked).toBeFalsy();

        const archiveButton = wrapper.find(ARCHIVE_HISTORY_BTN);
        expect(archiveButton.attributes("disabled")).toBeTruthy();
    });

    it("should enable the Archive button if there is an up to date export record and the confirm delete checkbox is checked", async () => {
        mockGetExportsApiResponse([RECENT_FILE_SOURCE_STORE_RESPONSE]);

        const wrapper = await mountComponentWithHistory(TEST_HISTORY as HistorySummary);

        const confirmDeleteCheckbox = wrapper.find(CONFIRM_DELETE_CHECKBOX);
        await confirmDeleteCheckbox.setChecked(true);
        expect((confirmDeleteCheckbox.element as HTMLInputElement).checked).toBeTruthy();

        const archiveButton = wrapper.find(ARCHIVE_HISTORY_BTN);
        expect(archiveButton.attributes("disabled")).toBeFalsy();
    });
});
