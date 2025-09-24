import { mount, shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";

import type { JobBaseModel } from "@/api/jobs";
import { statePlaceholders } from "@/composables/useInvocationGraph";

import { TEST_JOBS_BY_STATES } from "./test/jobStepUtils";
import TEST_JOBS_JSON from "./test/json/jobs.json";

import JobStep from "./JobStep.vue";

const TEST_INVOCATION_ID = "test-invocation-id";

const SELECTORS = {
    JOB_STATE_BUTTON_NAV: "nav",
    JOB_STATE_BUTTON: ".g-button",
    JOBS_TABLE: ".job-step-jobs",
    JOB_ROW: ".job-step-jobs > tbody > tr",
    STUBBED_JOB_DETAILS: "anonymous-stub",
};

describe("Job Step", () => {
    it("shows jobs grouped by state in tables when multiple jobs", async () => {
        const wrapper = mount(JobStep as object, {
            propsData: {
                jobs: TEST_JOBS_JSON,
                invocationId: TEST_INVOCATION_ID,
            },
        });
        await flushPromises();

        // verify that the job state buttons are rendered
        const nav = wrapper.find(SELECTORS.JOB_STATE_BUTTON_NAV);
        expect(nav.exists()).toBe(true);

        // there are as many buttons as there are unique job states in `jobs`
        const buttons = nav.findAll(SELECTORS.JOB_STATE_BUTTON);
        expect(buttons.length).toBe(Object.keys(TEST_JOBS_BY_STATES).length);

        const jobStates = Object.keys(TEST_JOBS_BY_STATES);

        // test each job state
        for (let i = 0; i < jobStates.length; i++) {
            const jobState = jobStates[i] as string;
            const expectedCount = TEST_JOBS_BY_STATES[jobState]?.length as number;

            // check that the button has the expected text
            expect(buttons.at(i).text()).toBe(
                `${expectedCount} job${expectedCount === 1 ? "" : "s"} ${statePlaceholders[jobState] || jobState}`,
            );

            // click the button to switch to this state
            await buttons.at(i).trigger("click");
            await flushPromises();

            // the clicked button should be pressed
            expect(buttons.at(i).classes()).toContain("g-pressed");

            // renders a table with jobs for the current state
            const tableRows = wrapper.find(SELECTORS.JOBS_TABLE).findAll(SELECTORS.JOB_ROW);
            expect(tableRows.length).toBe(expectedCount);

            // each row has the expected state (as the last cell in the row)
            tableRows.wrappers.forEach((tr) => {
                const cells = tr.findAll("td");
                expect(cells.at(cells.length - 1).text()).toBe(jobState);
            });
        }
    });

    it("reacts to job states changing when multiple jobs", async () => {
        const wrapper = mount(JobStep as object, {
            propsData: {
                jobs: TEST_JOBS_JSON,
                invocationId: TEST_INVOCATION_ID,
            },
        });
        await flushPromises();

        // NOTE: This test assumes that the first job in TEST_JOBS_JSON has state 'new', and there is only one job with that state.
        // That is because we will update that job to 'running' and expect the active/pressed button to change to 'running',
        // as there are no more jobs in 'new' state.

        let buttons = wrapper.find(SELECTORS.JOB_STATE_BUTTON_NAV).findAll(SELECTORS.JOB_STATE_BUTTON);
        expect(buttons.length).toBe(Object.keys(TEST_JOBS_BY_STATES).length);
        let firstButton = buttons.at(0);

        // verify initial data is displayed for 'new' state'
        expect(firstButton.classes()).toContain("g-pressed");
        expect(firstButton.text()).toBe("1 job new");

        // the table should show one job in 'new' state
        expect(wrapper.findAll(SELECTORS.JOB_ROW).length).toBe(1);
        expect(wrapper.find(SELECTORS.JOB_ROW).find("td:last-child").text()).toBe("new");

        // we have one running job already
        expect(buttons.at(1).text()).toBe("1 job running");

        // we trigger the state change by updating the first job's state from 'new' to 'running'
        const updatedJob = { ...TEST_JOBS_JSON[0], state: "running" };
        await wrapper.setProps({ jobs: [updatedJob, ...TEST_JOBS_JSON.slice(1)] });
        await flushPromises();

        // verify buttons have been updated
        buttons = wrapper.find(SELECTORS.JOB_STATE_BUTTON_NAV).findAll(SELECTORS.JOB_STATE_BUTTON);
        expect(buttons.length).toBe(Object.keys(TEST_JOBS_BY_STATES).length - 1);
        firstButton = buttons.at(0);

        // first button is now 'running' with 2 jobs
        expect(firstButton.classes()).toContain("g-pressed");
        expect(firstButton.text()).toBe("2 jobs running");

        // the table should now show 2 jobs in 'running' state
        expect(wrapper.findAll(SELECTORS.JOB_ROW).length).toBe(2);
        expect(wrapper.find(SELECTORS.JOB_ROW).find("td:last-child").text()).toBe("running");
    });

    it("just renders the job when only one job", async () => {
        const singleJob = TEST_JOBS_JSON.slice(0, 1)[0] as JobBaseModel;

        const wrapper = shallowMount(JobStep as object, {
            propsData: {
                jobs: [singleJob],
                invocationId: TEST_INVOCATION_ID,
            },
        });
        await flushPromises();

        expect(wrapper.find(SELECTORS.JOBS_TABLE).exists()).toBe(false);
        expect(wrapper.find(SELECTORS.JOB_STATE_BUTTON_NAV).exists()).toBe(false);

        const jobDetails = wrapper.find(SELECTORS.STUBBED_JOB_DETAILS);
        expect(jobDetails.exists()).toBe(true);

        expect(jobDetails.attributes()["jobid"]).toBe(singleJob.id);
        expect(jobDetails.attributes()["invocationid"]).toBe(TEST_INVOCATION_ID);
    });
});
