import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, suppressDebugConsole } from "@tests/jest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";

import { type HistorySummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { fetchHistoryExportRecords } from "@/api/histories.export";
import { type BrowsableFilesSourcePlugin } from "@/api/remoteFiles";
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

const REMOTE_FILES_API_RESPONSE: BrowsableFilesSourcePlugin[] = [
    {
        id: "test-posix-source",
        type: "posix",
        label: "TestSource",
        doc: "For testing",
        writable: true,
        browsable: true,
        requires_roles: undefined,
        requires_groups: undefined,
        supports: {
            pagination: false,
            search: false,
            sorting: false,
        },
        uri_root: "gxfiles://test-posix-source",
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

const { server, http } = useServerMock();

describe("HistoryExport.vue", () => {
    beforeEach(async () => {
        server.use(
            http.get("/api/histories/{history_id}", ({ response, params }) => {
                const historyId = params.history_id;
                if (historyId === FAKE_HISTORY_ID) {
                    return response(200).json(FAKE_HISTORY);
                }
            }),

            http.get("/api/remote_files/plugins", ({ response }) => {
                return response(200).json([]);
            })
        );
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
        server.use(
            http.get("/api/remote_files/plugins", ({ response }) => response(200).json(REMOTE_FILES_API_RESPONSE))
        );

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
        const zenodoPlugin: BrowsableFilesSourcePlugin = {
            id: "zenodo",
            type: "rdm",
            label: "Zenodo",
            doc: "For testing",
            writable: true,
            browsable: true,
            supports: {
                pagination: false,
                search: false,
                sorting: false,
            },
            uri_root: "zenodo://",
        };
        server.use(http.get("/api/remote_files/plugins", ({ response }) => response(200).json([zenodoPlugin])));

        const wrapper = await mountHistoryExport();

        expect(wrapper.find("#zenodo-file-source-tab").exists()).toBe(true);
    });

    it("should display the ZENODO tab if the user has a user-defined Zenodo file source", async () => {
        const userZenodoPlugin: BrowsableFilesSourcePlugin = {
            id: "998c5bba-b18f-4223-9c93-0f36fa2fdae8",
            type: "zenodo",
            label: "ZENODO",
            doc: "My integration with Zenodo",
            browsable: true,
            writable: true,
            requires_roles: null,
            requires_groups: null,
            url: "https://zenodo.org/",
            supports: {
                pagination: true,
                search: true,
                sorting: false,
            },
            uri_root: "gxuserfiles://998c5bba-b18f-4223-9c93-0f36fa2fdae8",
        };
        server.use(http.get("/api/remote_files/plugins", ({ response }) => response(200).json([userZenodoPlugin])));

        const wrapper = await mountHistoryExport();

        expect(wrapper.find("#zenodo-file-source-tab").exists()).toBe(true);
    });

    it("should not display a fatal error alert if the history is found and loaded", async () => {
        suppressDebugConsole(); // we rightfully debug message the fact we don't have a history in this test

        const wrapper = await mountHistoryExport();

        expect(wrapper.find("#fatal-error-alert").exists()).toBe(false);

        expect(wrapper.find("#history-name").exists()).toBe(true);
        expect(wrapper.find("#history-export-options").exists()).toBe(true);
        expect(wrapper.find("#direct-download-tab").exists()).toBe(true);
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

        expect(wrapper.find("#fatal-error-alert").exists()).toBe(true);

        expect(wrapper.find("#history-name").exists()).toBe(false);
        expect(wrapper.find("#history-export-options").exists()).toBe(false);
        expect(wrapper.find("#direct-download-tab").exists()).toBe(false);
    });
});
