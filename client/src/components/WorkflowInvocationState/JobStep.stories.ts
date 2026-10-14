import type { Meta, StoryObj } from "@storybook/vue3-vite";

import { INVOCATION, JOB_STEP_JOBS, jobStepHandlers } from "./test_fixtures";

import JobStep from "./JobStep.vue";

const meta = {
    title: "WorkflowInvocationState/JobStep",
    component: JobStep,
    args: { jobs: JOB_STEP_JOBS, invocationId: INVOCATION.id },
    parameters: { msw: { handlers: jobStepHandlers } },
} satisfies Meta<typeof JobStep>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A mapped concatenate step has new, running, and completed jobs; choose a state to inspect its jobs. */
export const MappedJobs: Story = {};

/** An unmapped step shows the new job's information, parameters, and metrics directly. */
export const SingleJob: Story = {
    args: { jobs: [JOB_STEP_JOBS[0]!] },
};

/** Before jobs have been created for this step. */
export const NoJobs: Story = {
    args: { jobs: [] },
};
