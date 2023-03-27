import { shallowMount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import {
    EXPIRED_STS_DOWNLOAD_RECORD,
    FILE_SOURCE_STORE_RECORD,
    RECENT_STS_DOWNLOAD_RECORD,
} from "@/components/Common/models/testData/exportData";
import flushPromises from "flush-promises";
import type { components } from "@/schema";
import { getLocalVue } from "@tests/jest/helpers";
import HistoryExport from "./HistoryExport.vue";
import { getExportRecords } from "./services";

const localVue = getLocalVue(true);

jest.mock("./services");
const mockGetExportRecords = getExportRecords as jest.MockedFunction<typeof getExportRecords>;
mockGetExportRecords.mockResolvedValue([]);

const FAKE_HISTORY_ID = "fake-history-id";
const REMOTE_FILES_API_ENDPOINT = new RegExp("/api/remote_files/plugins");

type FilesSourcePluginList = components["schemas"]["FilesSourcePlugin"][];
const REMOTE_FILES_API_RESPONSE: FilesSourcePluginList = [
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
];

async function mountHistoryExport() {
    const wrapper = shallowMount(HistoryExport, {
        propsData: { historyId: FAKE_HISTORY_ID },
        localVue,
    });
    await flushPromises();
    return wrapper;
}

describe("HistoryExport.vue", () => {
    let axiosMock: MockAdapter;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet(REMOTE_FILES_API_ENDPOINT).reply(200, []);
    });

    afterEach(() => {
        axiosMock.restore();
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
        mockGetExportRecords.mockResolvedValue([
            RECENT_STS_DOWNLOAD_RECORD,
            FILE_SOURCE_STORE_RECORD,
            EXPIRED_STS_DOWNLOAD_RECORD,
        ]);
        const wrapper = await mountHistoryExport();

        expect(wrapper.find("#previous-export-records").exists()).toBe(true);
    });

    it("should not render previous records when there is one or less records", async () => {
        mockGetExportRecords.mockResolvedValue([RECENT_STS_DOWNLOAD_RECORD]);
        const wrapper = await mountHistoryExport();

        expect(wrapper.find("#previous-export-records").exists()).toBe(false);
    });

    it("should display file sources tab if there are available", async () => {
        axiosMock.onGet(REMOTE_FILES_API_ENDPOINT).reply(200, REMOTE_FILES_API_RESPONSE);
        const wrapper = await mountHistoryExport();

        expect(wrapper.find("#direct-download-tab").exists()).toBe(true);
        expect(wrapper.find("#file-source-tab").exists()).toBe(true);
    });

    it("should not display file sources tab if there are no file sources available", async () => {
        const wrapper = await mountHistoryExport();

        expect(wrapper.find("#direct-download-tab").exists()).toBe(true);
        expect(wrapper.find("#file-source-tab").exists()).toBe(false);
    });
});
