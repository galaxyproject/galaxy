import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, suppressDebugConsole } from "@tests/jest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";

import type { HistorySummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { fetchHistoryExportRecords } from "@/api/histories.export";
import {
    EXPIRED_STS_DOWNLOAD_RECORD,
    FILE_SOURCE_STORE_RECORD,
    RECENT_STS_DOWNLOAD_RECORD,
} from "@/components/Common/models/testData/exportData";

import HistoryExport from "./HistoryExport.vue";

const localVue = getLocalVue(true);

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

const selectors = {
    historyName: "#history-name",
    latestExportRecord: "#latest-export-record",
    showPreviousExportRecordsButton: "#show-old-records-button",
    fatalErrorAlert: "#fatal-error-alert",
} as const;

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

const { server, http } = useServerMock();

describe("HistoryExport.vue", () => {
    beforeEach(async () => {
        server.use(
            http.get("/api/histories/{history_id}", ({ response, params }) => {
                const historyId = params.history_id;
                if (historyId === FAKE_HISTORY_ID) {
                    return response(200).json(FAKE_HISTORY);
                }
            })
        );
    });

    it("should render the history name", async () => {
        const wrapper = await mountHistoryExport();

        expect(wrapper.find(selectors.historyName).text()).toBe(FAKE_HISTORY.name);
    });

    it("should not display the latest export record if there is no export record", async () => {
        const wrapper = await mountHistoryExport();

        expect(wrapper.find(selectors.latestExportRecord).exists()).toBe(false);
    });

    it("should display the previous records button when there is more than one record", async () => {
        mockFetchExportRecords.mockResolvedValue([
            RECENT_STS_DOWNLOAD_RECORD,
            FILE_SOURCE_STORE_RECORD,
            EXPIRED_STS_DOWNLOAD_RECORD,
        ]);
        const wrapper = await mountHistoryExport();

        expect(wrapper.find(selectors.showPreviousExportRecordsButton).exists()).toBe(true);
    });

    it("should not display the previous records button when there is one or less records", async () => {
        mockFetchExportRecords.mockResolvedValue([RECENT_STS_DOWNLOAD_RECORD]);
        const wrapper = await mountHistoryExport();

        expect(wrapper.find(selectors.showPreviousExportRecordsButton).exists()).toBe(false);
    });

    it("should not display a fatal error alert if the history is found and loaded", async () => {
        suppressDebugConsole(); // we rightfully debug message the fact we don't have a history in this test

        const wrapper = await mountHistoryExport();

        expect(wrapper.find(selectors.fatalErrorAlert).exists()).toBe(false);
        expect(wrapper.find(selectors.historyName).exists()).toBe(true);
    });

    it("should not render the UI and display a fatal error message if the history cannot be found or loaded", async () => {
        server.use(
            http.get("/api/histories/{history_id}", ({ response }) =>
                response("4XX").json(
                    {
                        err_code: 404,
                        err_msg: "History not found",
                    },
                    { status: 404 }
                )
            )
        );

        const wrapper = await mountHistoryExport();

        expect(wrapper.find(selectors.fatalErrorAlert).exists()).toBe(true);
        expect(wrapper.find(selectors.historyName).exists()).toBe(false);
    });
});
