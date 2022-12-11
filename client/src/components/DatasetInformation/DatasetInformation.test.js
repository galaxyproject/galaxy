import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import DatasetInformation from "./DatasetInformation";
import datasetResponse from "./testData/datasetResponse";
import flushPromises from "flush-promises";
import { parseISO } from "date-fns";
import { formatInTimeZone } from "date-fns-tz";

const HDA_ID = "FOO_HDA_ID";

const mockDatasetProvider = {
    render() {
        return this.$scopedSlots.default({
            loading: false,
            result: datasetResponse,
        });
    },
};

const localVue = getLocalVue();

describe("DatasetInformation/DatasetInformation", () => {
    let wrapper;
    let datasetInfoTable;
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet(new RegExp(`api/configuration/decode/*`)).reply(200, { decoded_id: 123 });
    });

    afterEach(() => {
        axiosMock.restore();
    });

    beforeEach(async () => {
        const propsData = {
            hda_id: HDA_ID,
        };

        wrapper = mount(DatasetInformation, {
            propsData,
            stubs: {
                DatasetProvider: mockDatasetProvider,
            },
            localVue,
        });
        datasetInfoTable = wrapper.find("#dataset-details");
        await flushPromises();
    });

    it("dataset information should exist", async () => {
        // table should exist
        expect(datasetInfoTable).toBeTruthy();
        const rows = datasetInfoTable.findAll("tbody > tr");
        // should contain 11 rows
        expect(rows.length).toBe(11);
    });

    it("filesize should be formatted", async () => {
        const filesize = datasetInfoTable.find("#filesize > strong");
        expect(filesize.html()).toBe(`<strong>${datasetResponse.file_size}</strong>`);
    });

    it("Date should be formatted", async () => {
        const date = datasetInfoTable.find(".utc-time").text();
        const parsedDate = parseISO(`${datasetResponse.create_time}Z`);
        const formattedDate = `${formatInTimeZone(parsedDate, "Etc/Zulu", "eeee MMM do H:mm:ss yyyy")} UTC`;
        expect(date).toBe(formattedDate);
    });

    it("Table should render data accordingly", async () => {
        const rendered_entries = [
            { htmlAttribute: "number", backend_key: "hid" },
            { htmlAttribute: "name", backend_key: "name" },
            { htmlAttribute: "dbkey", backend_key: "metadata_dbkey" },
            { htmlAttribute: "format", backend_key: "file_ext" },
            { htmlAttribute: "file-contents", backend_key: "download_url" },
        ];

        rendered_entries.forEach((entry) => {
            const renderedText = datasetInfoTable.find(`#${entry.htmlAttribute}`).text();
            if (entry.htmlAttribute === "file-contents") {
                expect(renderedText).toBe("contents");
            } else {
                expect(renderedText).toBe(datasetResponse[entry.backend_key].toString());
            }
        });
    });
});
