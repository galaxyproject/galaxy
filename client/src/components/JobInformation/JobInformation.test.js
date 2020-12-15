import Vuex from "vuex";
import { mount, createLocalVue } from "@vue/test-utils";
import JobInformation from "./JobInformation";
import datasetResponse from "components/DatasetInformation/testData/datasetResponse";
import jobResponse from "./testData/jobInformationResponse.json";

import flushPromises from "flush-promises";
import createCache from "vuex-cache";

jest.mock("app");

const HDA_ID = "FOO_HDA_ID";
const JOB_ID = "test_id";

const localVue = createLocalVue();
localVue.use(Vuex);

const jobStore = new Vuex.Store({
    plugins: [createCache()],
    modules: {
        jobStore: {
            actions: {
                fetchDataset: jest.fn(),
                fetchJob: jest.fn(),
            },
            getters: {
                dataset: (state) => (hda_id) => {
                    return datasetResponse;
                },
                job: (state) => (hda_id) => {
                    return jobResponse;
                },
            },
        },
    },
});

describe("JobInformation/JobInformation.vue", () => {
    let wrapper;
    let jobInfoTable;

    const verifyValues = (rendered_entries, infoTable, backendResponse) => {
        rendered_entries.forEach((entry) => {
            const renderedText = infoTable.find(`#${entry.id}`).text();
            const backendText = entry.wrapped_in_brackets
                ? `(${backendResponse[entry.backend_key]})`
                : backendResponse[entry.backend_key];
            expect(renderedText).toBe(backendText.toString());
        });
    };

    beforeEach(async () => {
        const propsData = {
            hda_id: HDA_ID,
            job_id: JOB_ID,
        };

        wrapper = mount(JobInformation, {
            store: jobStore,
            propsData,
            localVue,
        });
        jobInfoTable = wrapper.find("#job-information");
        await flushPromises();
    });

    it("job information table should be rendered", async () => {
        // table should exist
        expect(jobInfoTable).toBeTruthy();
        const rows = jobInfoTable.findAll("tr");
        // should contain 9 rows
        expect(rows.length).toBe(12);
    });

    it("stdout, stderr links", async () => {
        ["stderr", "stdout"].forEach((std) => {
            const rendered_link = jobInfoTable.find(`#${std} > a`);
            expect(rendered_link.text()).toBe(std);
            expect(rendered_link.attributes("href")).toBe(`/datasets/${HDA_ID}/${std}`);
        });
    });

    it("job messages", async () => {
        const rendered_link = jobInfoTable.findAll(`#job-messages li`);
        expect(rendered_link.length).toBe(jobResponse.job_messages.length);
        for (let i = 0; i < rendered_link.length; i++) {
            const msg = rendered_link.at(i).text();
            expect(jobResponse.job_messages.includes(msg));
        }
    });

    it("job_information API content", async () => {
        const rendered_entries = [
            { id: "galaxy-tool-id", backend_key: "tool_id" },
            { id: "galaxy-tool-version", backend_key: "tool_version" },
            { id: "encoded-job-id", backend_key: "id" },
            { id: "encoded-copied-from-job-id", backend_key: "copied_from_job_id" },
        ];
        verifyValues(rendered_entries, jobInfoTable, jobResponse);
    });

    it("dataset API content", async () => {
        const rendered_entries = [
            { id: "file_name", backend_key: "file_name" },
            { id: "dataset-uuid", backend_key: "uuid" },
            { id: "history_id", backend_key: "history_id" },
            { id: "history-dataset-id", backend_key: "dataset_id", wrapped_in_brackets: true },
            { id: "dataset-id", backend_key: "id" },
        ];
        verifyValues(rendered_entries, jobInfoTable, datasetResponse);
    });
});
