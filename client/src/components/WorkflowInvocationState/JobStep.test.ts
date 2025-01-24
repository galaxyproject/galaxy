import { createTestingPinia } from "@pinia/testing";
import { createLocalVue, mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import type { JobDisplayParametersSummary, ShowFullJobResponse } from "@/api/jobs";
import paramResponse from "@/components/JobParameters/parameters-response.json";

import jobs from "./test/json/jobs.json";

import JobStep from "./JobStep.vue";

const localVue = createLocalVue();

const { server, http } = useServerMock();

const SELECTORS = {
    JOB_TABS_LIST: ".nav-pills",
    JOB_TAB: ".nav-link",
    JOB_CONTENT: "[data-description='workflow invocation job'] > .card-body",
};

describe("DatasetUIWrapper.vue with Dataset", () => {
    let wrapper: Wrapper<Vue>;
    let propsData;
    let iteration: "base" | "state_change" = "base";
    const pinia = createTestingPinia();

    function getSummary(job_id: string) {
        let summary = jobs.find((s) => s.id === job_id);
        if (summary && iteration === "state_change" && job_id === "1") {
            summary.state = "running";
        }
        if (job_id === "3") {
            summary = { ...(jobs[0] as any), id: "3" };
        }
        return summary as ShowFullJobResponse;
    }

    beforeEach(async () => {
        server.use(
            http.get("/api/jobs/{job_id}", ({ response, params }) => {
                const { job_id } = params;
                const summary = getSummary(job_id);
                if (!summary) {
                    return response("4XX").json({ err_msg: "Job not found", err_code: 404 }, { status: 404 });
                }
                return response(200).json(summary);
            })
        );
        server.use(
            http.get("/api/invocations", ({ response }) => {
                return response(200).json([]);
            })
        );
        server.use(
            http.get("/api/jobs/{job_id}/parameters_display", ({ response }) => {
                return response(200).json(paramResponse as JobDisplayParametersSummary);
            })
        );
        server.use(
            http.get("/api/datasets/{dataset_id}", ({ response, params }) => {
                const { dataset_id } = params;
                // We need to use untyped here because this endpoint is not
                // described in the OpenAPI spec due to its complexity for now.
                return response.untyped(
                    HttpResponse.json({
                        id: dataset_id,
                        creating_job: `job-${dataset_id}`,
                    })
                );
            })
        );

        propsData = {
            jobs: jobs,
        };
        wrapper = mount(JobStep as object, {
            localVue,
            propsData,
            stubs: {
                BPopover: true,
                ContentItem: true,
                FontAwesomeIcon: true,
                JobInformation: true,
                JobParameters: true,
                BTooltip: true,
                LoadingSpan: true,
            },
            pinia,
        });
        await flushPromises();
    });
    test("shows as many tabs as jobs and clicking tab changes shown job", async () => {
        // it renders 2 jobs in 2 tabs with states
        const ulTabs = wrapper.find(SELECTORS.JOB_TABS_LIST);
        const liTabs = ulTabs.findAll(SELECTORS.JOB_TAB);
        expect(liTabs.length).toBe(jobs.length);

        const jobsContents = wrapper.findAll(SELECTORS.JOB_CONTENT);
        expect(jobsContents.length).toBe(jobs.length);

        liTabs.wrappers.forEach((liTab, i) => {
            expect(jobs[i]).toBeTruthy();
            expect(liTab.text()).toEqual(jobs[i]?.state);
            // expect the first job to be shown and rest to be hidden
            expect(liTab.attributes("aria-selected")).toEqual(i === 0 ? "true" : "false");
            expect(jobsContents.at(i).attributes("style")).toEqual(i === 0 ? "" : "display: none;");
        });

        // click on the second tab
        await liTabs.at(1).trigger("click");
        await flushPromises();

        // expect the second job to be shown and rest to be hidden
        jobsContents.wrappers.forEach((jobContent, i) => {
            expect(jobContent.attributes("style")).toEqual(i === 1 ? "" : "display: none;");
            expect(liTabs.at(i).attributes("aria-selected")).toEqual(i === 1 ? "true" : "false");
        });
    });
    test("it reacts to prop update", async () => {
        // verify initial data is displayed for first tab
        expect(wrapper.find(SELECTORS.JOB_TAB).text()).toBe("new");

        // update first job to change state from 'new' to 'running'
        iteration = "state_change";
        // technically, we only need to trigger a prop update, the state
        // change is handled by the mock server in `getSummary`
        const updatedJob = { ...jobs[0], state: "running" };
        await wrapper.setProps({ jobs: [updatedJob, ...jobs.slice(1)] });
        await flushPromises();

        // verify new data is displayed
        expect(wrapper.find(SELECTORS.JOB_TAB).text()).toBe("running");

        // update data
        const additionalJob = { ...jobs[0], id: "3" };
        await wrapper.setProps({ jobs: [...jobs, additionalJob] });
        await flushPromises();
        // verify new data is displayed
        const ulTabs = wrapper.find(SELECTORS.JOB_TABS_LIST);
        const liTabs = ulTabs.findAll(SELECTORS.JOB_TAB);
        expect(liTabs.length).toBe(jobs.length + 1);
    });
});
