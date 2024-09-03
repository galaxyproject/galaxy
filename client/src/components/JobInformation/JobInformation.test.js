import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";

import jobResponse from "./testData/jobInformationResponse.json";

import JobInformation from "./JobInformation.vue";

jest.mock("app");

const JOB_ID = "test_id";

const localVue = getLocalVue();

const { server, http } = useServerMock();

describe("JobInformation/JobInformation.vue", () => {
    let wrapper;
    let jobInfoTable;

    beforeEach(() => {
        server.use(
            http.get("/api/configuration/decode/{encoded_id}", ({ response }) => {
                return response(200).json({ decoded_id: 123 });
            }),
            http.get("/api/jobs/{job_id}", ({ response }) => {
                return response(200).json(jobResponse);
            }),
            http.get("/api/invocations", ({ response }) => {
                return response(200).json([]);
            })
        );
    });

    const verifyValues = (rendered_entries, infoTable, backendResponse) => {
        rendered_entries.forEach((entry) => {
            const renderedText = infoTable.find(`#${entry.id}`).text();
            const backendText = entry.wrapped_in_brackets
                ? `(${backendResponse[entry.backend_key]})`
                : backendResponse[entry.backend_key];
            // use includes because we append the decoded id
            expect(renderedText.includes(backendText.toString())).toBeTruthy();
        });
    };

    beforeEach(async () => {
        const propsData = {
            job_id: JOB_ID,
        };
        wrapper = mount(JobInformation, {
            propsData,
            localVue,
        });
        await flushPromises();
        jobInfoTable = wrapper.find("#job-information");
    });

    it("job information table should be rendered", async () => {
        // table should exist
        expect(jobInfoTable).toBeTruthy();
        const rows = jobInfoTable.findAll("tr");
        // should contain 9 rows
        expect(rows.length).toBe(9);
    });

    it("stdout and stderr should be rendered", async () => {
        ["stdout", "stderr"].forEach((std) => {
            const label = jobInfoTable.find("#" + std);
            const value = label.find(".code");
            expect(value.text()).toBe(std);
        });
    });

    it("job messages", async () => {
        const rendered_link = jobInfoTable.findAll(`#job-messages .job-message`);
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
});
