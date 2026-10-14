import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, waitFor, within } from "storybook/test";

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
    play: async ({ canvas, step }) => {
        await step("Read the single job directly without grouped jobs", async () => {
            await waitFor(() => expect(canvas.getByText("cat_data_and_sleep", { exact: true })).toBeVisible(), {
                timeout: 5000,
            });
            await expect(canvas.getByRole("heading", { name: "Job Execution Details" })).toBeVisible();
            await expect(canvas.getByRole("heading", { name: "Job Parameters" })).toBeVisible();
            await expect(canvas.getByRole("heading", { name: "Job Metrics" })).toBeVisible();
            await expect(canvas.queryByRole("navigation")).not.toBeInTheDocument();
            await expect(canvas.queryByRole("columnheader", { name: "Job ID" })).not.toBeInTheDocument();
        });
    },
};

/** Before jobs have been created for this step. */
export const NoJobs: Story = {
    args: { jobs: [] },
    play: async ({ canvas, step }) => {
        await step("Read why no job details are available", async () => {
            const message = await canvas.findByRole("status");
            await expect(message).toBeVisible();
            await expect(message).toHaveTextContent(/^No jobs found for this step\.$/);
            await expect(canvas.queryByRole("navigation")).not.toBeInTheDocument();
            await expect(canvas.queryByRole("columnheader", { name: "Job ID" })).not.toBeInTheDocument();
            await expect(canvas.queryByRole("heading", { name: "Job Execution Details" })).not.toBeInTheDocument();
        });
    },
};

/** Choose each mapped job state and see only that state's jobs in the table. */
export const FiltersMappedJobsByState: Story = {
    play: async ({ canvas, userEvent, step }) => {
        const groups = [
            { label: "1 job new", state: "new", ids: ["sample-job-0"] },
            { label: "1 job running", state: "running", ids: ["sample-job-1"] },
            { label: "2 jobs successful", state: "ok", ids: ["sample-job-2", "sample-job-3"] },
        ];
        await step("See every available job state", async () => {
            const navigation = await canvas.findByRole("navigation");
            await expect(navigation).toBeVisible();
            const buttons = within(navigation).getAllByRole("button");
            await expect(buttons).toHaveLength(groups.length);
            for (const [index, group] of groups.entries()) {
                await expect(buttons[index]).toHaveAccessibleName(group.label);
            }
        });
        for (const group of groups) {
            await step(`Show ${group.label}`, async () => {
                await userEvent.click(
                    within(canvas.getByRole("navigation")).getByRole("button", { name: group.label }),
                );
                await waitFor(() => {
                    const table = canvas.getByRole("table");
                    const rows = within(table)
                        .getAllByRole("row")
                        .filter((row) => within(row).queryAllByRole("cell").length > 0);
                    expect(rows).toHaveLength(group.ids.length);
                    expect(rows.map((row) => within(row).getAllByRole("cell")[0]?.textContent?.trim())).toEqual(
                        group.ids,
                    );
                    for (const row of rows) {
                        const cells = within(row).getAllByRole("cell");
                        expect(cells[cells.length - 1]).toHaveTextContent(new RegExp(`^${group.state}$`));
                    }
                });
            });
        }
    },
};
