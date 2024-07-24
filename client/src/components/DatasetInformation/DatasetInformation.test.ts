import { getLocalVue } from "@tests/jest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { format, parseISO } from "date-fns";
import flushPromises from "flush-promises";

import DatasetInformation from "./DatasetInformation.vue";

const HDA_ID = "FOO_HDA_ID";

interface DatasetResponse {
    id: string;
    hid: number;
    uuid: string;
    name: string;
    file_ext: string;
    file_name: string;
    file_size: number;
    dataset_id: string;
    history_id: string;
    create_time: string;
    metadata_dbkey: string;
    [key: string]: any;
}

const datasetResponse: DatasetResponse = {
    id: "FOO_HDA_ID",
    hid: 32,
    uuid: "5e89abe4-e8f7-468a-9ef1-d4e322183fa5",
    name: "Add column on data 31",
    file_size: 93,
    file_ext: "txt",
    dataset_id: "201592c8e20dac24",
    history_id: "6fc9fbb81c497f69",
    create_time: "2020-09-28T15:54:04.803756",
    metadata_dbkey: "?",
    file_name: "/home/oleg/galaxy/database/objects/5/e/8/dataset_5e89abe4-e8f7-468a-9ef1-d4e322183fa5.dat",
};

const localVue = getLocalVue();

describe("DatasetInformation/DatasetInformation", () => {
    let wrapper: Wrapper<Vue>;
    let axiosMock: MockAdapter;
    let datasetInfoTable: Wrapper<Vue>;

    afterEach(() => {
        axiosMock.restore();
    });

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet(new RegExp(`api/configuration/decode/*`)).reply(200, { decoded_id: 123 });

        wrapper = mount(DatasetInformation as object, {
            propsData: {
                dataset: datasetResponse,
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

    it("file size should be formatted", async () => {
        const fileSize = datasetInfoTable.find("#file-size > strong");

        expect(fileSize.html()).toBe(`<strong>${datasetResponse.file_size}</strong>`);
    });

    it("Date should be formatted", async () => {
        const date = datasetInfoTable.find(".utc-time").text();

        const parsedDate = parseISO(`${datasetResponse.create_time}Z`);
        const formattedDate = format(parsedDate, "eeee MMM do H:mm:ss yyyy zz");

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
