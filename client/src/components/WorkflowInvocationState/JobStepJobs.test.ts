import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import type { JobDisplayParametersSummary, ShowFullJobResponse } from "@/api/jobs";
import paramResponse from "@/components/JobParameters/parameters-response.json";

import { TEST_JOBS_BY_STATES } from "./test/jobStepUtils";
import TEST_JOBS_JSON from "./test/json/jobs.json";

import JobStepJobs from "./JobStepJobs.vue";

const localVue = getLocalVue();

const { server, http } = useServerMock();

const TEST_NEW_JOB_ID = "sample-job-NEW";

const SELECTORS = {
    JOBS_TABLE: ".job-step-jobs",
    JOB_ROW: ".job-step-jobs > tbody > tr",
    JOB_CONTENT: ".g-modal-content",
    JOB_INFORMATION_TABLE: "table#job-information",
};

describe("JobStepJobs", () => {
    function getSummary(job_id: string) {
        let summary = TEST_JOBS_JSON.find((s) => s.id === job_id);
        // special case when we want to test adding a new job
        if (job_id === TEST_NEW_JOB_ID) {
            summary = { ...TEST_JOBS_JSON[0]!, id: TEST_NEW_JOB_ID, state: "new" };
        }
        return summary as ShowFullJobResponse;
    }

    beforeEach(() => {
        server.use(
            http.get("/api/jobs/{job_id}", ({ response, params }) => {
                const { job_id } = params;
                const summary = getSummary(job_id);
                if (!summary) {
                    return response("4XX").json({ err_msg: "Job not found", err_code: 404 }, { status: 404 });
                }
                return response(200).json(summary);
            }),
        );
        server.use(
            http.get("/api/jobs/{job_id}/parameters_display", ({ response }) => {
                return response(200).json(paramResponse as JobDisplayParametersSummary);
            }),
        );
        server.use(
            http.get("/api/datasets/{dataset_id}", ({ response, params }) => {
                const { dataset_id } = params;
                return response.untyped(
                    HttpResponse.json({
                        id: dataset_id,
                        creating_job: `job-${dataset_id}`,
                    }),
                );
            }),
        );
    });

    it("renders a jobs table which allows opening a job details modal", async () => {
        const wrapper = mount(JobStepJobs as object, {
            propsData: {
                jobs: TEST_JOBS_BY_STATES["ok"],
                invocationId: "test-invocation-id",
                currentPage: 1,
                sortDesc: true,
                perPage: 10,
            },
            localVue,
            pinia: createTestingPinia(),
            stubs: {
                ContentItem: true,
                FontAwesomeIcon: true,
                JobInformation: true,
                JobParameters: true,
                RouterLink: true,
            },
        });
        await flushPromises();

        const jobsTable = wrapper.find(SELECTORS.JOBS_TABLE);
        expect(jobsTable.exists()).toBe(true);

        const tableRows = jobsTable.findAll(SELECTORS.JOB_ROW);
        expect(tableRows.length).toBe(TEST_JOBS_BY_STATES["ok"]?.length);

        // initially the modal content is empty
        expect(wrapper.find(SELECTORS.JOB_CONTENT).text()).toBe("");

        // click on a row and expect the modal to be populated
        await tableRows.at(0).trigger("click");
        await flushPromises();

        expect(wrapper.find(SELECTORS.JOB_CONTENT).text()).not.toBe("");
        expect(wrapper.find(SELECTORS.JOB_INFORMATION_TABLE).exists()).toBe(true);

        expect(wrapper.find("#galaxy-tool-id").text()).toBe(TEST_JOBS_BY_STATES["ok"]?.[0]?.tool_id);
    });
});
