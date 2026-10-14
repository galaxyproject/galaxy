import { createTestingPinia } from "@pinia/testing";
import { composeStories } from "@storybook/vue3-vite";
import { nth } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { disposePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { computed, type Ref, ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type { JobBaseModel } from "@/api/jobs";
import type * as JobDetailsModule from "@/composables/jobDetails";
import { statePlaceholders } from "@/composables/useInvocationGraph";

import * as JobStepStories from "./JobStep.stories";
import { TEST_JOBS_BY_STATES } from "./test/jobStepUtils";
import { JOB_STEP_JOBS as TEST_JOBS_JSON } from "./test_fixtures";

import JobStep from "./JobStep.vue";
import JobDetails from "@/components/JobInformation/JobDetails.vue";

const stories = composeStories(JobStepStories);
const mountStory = useStoryMount();
const TEST_INVOCATION_ID = JobStepStories.default.args.invocationId;

const mockedJobsById = ref<Record<string, JobBaseModel>>({});

function mockJobs(jobs: JobBaseModel[]) {
    mockedJobsById.value = Object.fromEntries(jobs.map((job) => [job.id, job]));
}

// Since `JobState` fetches its job via `useJobDetails`, we need to mock that composable to return
// jobs reactively, as the table changes values as the states change.
vi.mock("@/composables/jobDetails", async (importOriginal) => ({
    ...(await importOriginal<typeof JobDetailsModule>()),
    useJobDetails: (jobId: Ref<string | undefined>) => ({
        job: computed(() => (jobId.value ? (mockedJobsById.value[jobId.value] ?? null) : null)),
        error: computed(() => null),
        loading: computed(() => false),
    }),
}));

const { server, http } = useServerMock();

beforeEach(() => {
    server.use(http.get("/api/invocations/{invocation_id}/metrics", ({ response }) => response(200).json([])));
});

const SELECTORS = {
    JOB_STATE_BUTTON_NAV: "nav",
    JOB_STATE_BUTTON: ".g-button",
    JOBS_TABLE: ".job-step-jobs",
    JOB_ROW: ".job-step-jobs .g-table tbody > tr:not(.g-table-details-row):not(.g-table-empty-row)",
};

function jobStepMountOptions(jobs: JobBaseModel[] = TEST_JOBS_JSON) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    onTestFinished(() => disposePinia(pinia));
    return {
        props: { jobs, invocationId: TEST_INVOCATION_ID },
        global: { plugins: [pinia] },
    };
}

describe("Job Step", () => {
    enableAutoUnmount(afterEach);
    afterEach(async () => {
        // Finish the mounted table's pending store/render work before disposing its resources.
        await flushPromises();
    });

    it("shows jobs grouped by state in tables when multiple jobs", async () => {
        mockJobs(TEST_JOBS_JSON);
        const wrapper = mountStory(stories.MappedJobs);
        await flushPromises();

        // verify that the job state buttons are rendered
        const nav = wrapper.find(SELECTORS.JOB_STATE_BUTTON_NAV);
        expect(nav.exists()).toBe(true);

        // there are as many buttons as there are unique job states in `jobs`
        const buttons = nav.findAll(SELECTORS.JOB_STATE_BUTTON);
        expect(buttons.length).toBe(Object.keys(TEST_JOBS_BY_STATES).length);

        const jobStates = Object.entries(TEST_JOBS_BY_STATES);

        // test each job state
        for (const [i, [jobState, stateJobs]] of jobStates.entries()) {
            const expectedCount = stateJobs.length;

            // check that the button has the expected text
            expect(nth(buttons, i).text()).toBe(
                `${expectedCount} job${expectedCount === 1 ? "" : "s"} ${statePlaceholders[jobState] || jobState}`,
            );

            // click the button to switch to this state
            await nth(buttons, i).trigger("click");
            await flushPromises();

            // the clicked button should be pressed
            expect(nth(buttons, i).classes()).toContain("g-pressed");

            // renders a table with jobs for the current state
            const tableRows = wrapper.get(SELECTORS.JOBS_TABLE).findAll(SELECTORS.JOB_ROW);
            expect(tableRows.length).toBe(expectedCount);

            // each row has the expected state (as the last cell in the row)
            tableRows.forEach((tr) => {
                const cells = tr.findAll("td");
                expect(nth(cells, -1).text()).toBe(jobState);
            });
        }
    });

    it("reacts to job states changing when multiple jobs", async () => {
        mockJobs(TEST_JOBS_JSON as JobBaseModel[]);
        const wrapper = mount(JobStep, jobStepMountOptions());
        await flushPromises();

        // NOTE: This test assumes that the first job in TEST_JOBS_JSON has state 'new', and there is only one job with that state.
        // That is because we will update that job to 'running' and expect the active/pressed button to change to 'running',
        // as there are no more jobs in 'new' state.

        let buttons = wrapper.get(SELECTORS.JOB_STATE_BUTTON_NAV).findAll(SELECTORS.JOB_STATE_BUTTON);
        expect(buttons.length).toBe(Object.keys(TEST_JOBS_BY_STATES).length);
        let firstButton = nth(buttons, 0);

        // verify initial data is displayed for 'new' state'
        expect(firstButton.classes()).toContain("g-pressed");
        expect(firstButton.text()).toBe("1 job new");

        // the table should show one job in 'new' state
        expect(wrapper.findAll(SELECTORS.JOB_ROW).length).toBe(1);
        expect(wrapper.get(SELECTORS.JOB_ROW).get("td:last-child").text()).toBe("new");

        // we have one running job already
        expect(nth(buttons, 1).text()).toBe("1 job running");

        // we trigger the state change by updating the first job's state from 'new' to 'running'
        const updatedJob: JobBaseModel = { ...nth(TEST_JOBS_JSON, 0), state: "running" };
        mockJobs([updatedJob, ...(TEST_JOBS_JSON.slice(1) as JobBaseModel[])]);
        await wrapper.setProps({ jobs: [updatedJob, ...TEST_JOBS_JSON.slice(1)] });
        await flushPromises();

        // verify buttons have been updated
        buttons = wrapper.get(SELECTORS.JOB_STATE_BUTTON_NAV).findAll(SELECTORS.JOB_STATE_BUTTON);
        expect(buttons.length).toBe(Object.keys(TEST_JOBS_BY_STATES).length - 1);
        firstButton = nth(buttons, 0);

        // first button is now 'running' with 2 jobs
        expect(firstButton.classes()).toContain("g-pressed");
        expect(firstButton.text()).toBe("2 jobs running");

        // the table should now show 2 jobs in 'running' state
        expect(wrapper.findAll(SELECTORS.JOB_ROW).length).toBe(2);
        expect(wrapper.get(SELECTORS.JOB_ROW).get("td:last-child").text()).toBe("running");
    });

    it("just renders the job when only one job", async () => {
        const singleJob = nth(TEST_JOBS_JSON, 0);

        mockJobs([singleJob]);
        const wrapper = mountStory(stories.SingleJob);
        await flushPromises();

        expect(wrapper.find(SELECTORS.JOBS_TABLE).exists()).toBe(false);
        expect(wrapper.find(SELECTORS.JOB_STATE_BUTTON_NAV).exists()).toBe(false);

        const jobDetails = wrapper.findComponent(JobDetails);
        expect(jobDetails.exists()).toBe(true);

        expect(jobDetails.props("jobId")).toBe(singleJob.id);
        expect(jobDetails.props("invocationId")).toBe(TEST_INVOCATION_ID);
    });
});
