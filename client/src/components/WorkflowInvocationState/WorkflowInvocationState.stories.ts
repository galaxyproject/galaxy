import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeHistorySummaryExtended } from "@tests/test-data";
import { getFakeWorkflowSummary } from "@tests/test-data/workflows";
import { HttpResponse } from "msw";
import { expect, within } from "storybook/test";
import { computed, h } from "vue";

import { http } from "@/api/client/__mocks__/http";
import { getGalaxyInstance, setGalaxyInstance } from "@/app";
import { GalaxyApp } from "@/app/galaxy";
import { typesAndMappingHandler } from "@/components/Datatypes/test_fixtures";
import datasetData from "@/components/providers/test/json/Dataset.json";
import invocationData from "@/components/Workflow/test/json/invocation.json";
import { useInvocationStore } from "@/stores/invocationStore";

import WorkflowInvocationState from "./WorkflowInvocationState.vue";

const INPUT_STEP = invocationData.steps[0]!;
const INPUT_DATASET = invocationData.inputs["0"];

/** No jobs left to run: the summary of an invocation that only takes an input. */
const TERMINAL_JOBS = { model: "WorkflowInvocation", states: {}, populated_state: "ok" };

/** Answers the invocation's jobs summary. */
function jobsSummary(summary: object) {
    return http.get("/api/invocations/{invocation_id}/jobs_summary", ({ response }) =>
        response.untyped(HttpResponse.json(summary)),
    );
}

/** Answers the invocation, as `invocation.json` with `overrides`. */
function invocation(overrides: object = {}) {
    return http.get("/api/invocations/{invocation_id}", ({ response }) =>
        response.untyped(HttpResponse.json({ ...invocationData, ...overrides })),
    );
}

/** The workflow that was run, as the graph loads it: one dataset input. */
const EDITOR_WORKFLOW = {
    id: "workflow-id",
    name: "Test Workflow",
    version: 0,
    annotation: "",
    tags: [],
    comments: [],
    steps: {
        0: {
            id: 0,
            type: "data_input",
            label: INPUT_STEP.workflow_step_label,
            name: "Input dataset",
            content_id: null,
            tool_state: {},
            errors: null,
            inputs: [],
            outputs: [{ name: "output", extensions: ["input"], optional: false }],
            annotation: "",
            post_job_actions: {},
            uuid: INPUT_STEP.workflow_step_uuid,
            workflow_outputs: [],
            input_connections: {},
            position: { left: 0, top: 0 },
        },
    },
};

/** The workflow graph draws its nodes with the app's legacy Galaxy instance. */
const withGalaxyInstance: Decorator = (story) => ({
    setup() {
        if (!getGalaxyInstance()) {
            setGalaxyInstance(new GalaxyApp({ config: { enable_tool_recommendations: false } }));
        }
    },
    render: () => h(story()),
});

/**
 * The invocation was opened before, so the store still holds it and its job summaries: the page
 * shows them at once and only polls for what isn't final. Renders the story once they're loaded,
 * or once loading the invocation failed.
 */
const withInvocationOpenedBefore: Decorator = (story, { args }) => ({
    setup() {
        const invocationStore = useInvocationStore();
        const id = args.invocationId as string;
        const loaded = computed(
            () =>
                Boolean(invocationStore.getInvocationLoadError(id)) ||
                Boolean(
                    invocationStore.getInvocationById(id) &&
                        invocationStore.getInvocationJobsSummaryById(id) &&
                        invocationStore.getInvocationStepJobsSummaryById(id),
                ),
        );
        return () => (loaded.value ? h(story()) : null);
    },
});

const meta = {
    title: "WorkflowInvocationState/WorkflowInvocationState",
    component: WorkflowInvocationState,
    decorators: [withGalaxyInstance, withInvocationOpenedBefore],
    args: { invocationId: invocationData.id, isFullPage: true },
    parameters: {
        msw: {
            handlers: {
                invocation: invocation(),
                jobsSummary: jobsSummary(TERMINAL_JOBS),
                // One finished job for every story; the steps view doesn't follow the jobs summary.
                stepJobsSummary: http.get("/api/invocations/{invocation_id}/step_jobs_summary", ({ response }) =>
                    response.untyped(
                        HttpResponse.json([{ id: "job-id", model: "Job", populated_state: "ok", states: { ok: 1 } }]),
                    ),
                ),
                workflow: http.get("/api/workflows/{workflow_id}", ({ response }) =>
                    response.untyped(
                        HttpResponse.json({
                            ...getFakeWorkflowSummary({ latest_workflow_id: invocationData.workflow_id }),
                            version: 0,
                        }),
                    ),
                ),
                // Not in the API schema: the graph loads the editor view with axios.
                workflowGraph: http.untyped.get("/api/workflows/:workflow_id/download", () =>
                    HttpResponse.json(EDITOR_WORKFLOW),
                ),
                history: http.get("/api/histories/{history_id}", ({ response }) =>
                    response.untyped(
                        HttpResponse.json(
                            getFakeHistorySummaryExtended({ id: invocationData.history_id, name: "RNA-seq run" }),
                        ),
                    ),
                ),
                inputDataset: http.get("/api/datasets/{dataset_id}", ({ response }) =>
                    response.untyped(
                        HttpResponse.json({
                            ...datasetData,
                            id: INPUT_DATASET.id,
                            history_id: invocationData.history_id,
                        }),
                    ),
                ),
                typesAndMapping: typesAndMappingHandler,
            },
        },
    },
} satisfies Meta<typeof WorkflowInvocationState>;

export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/** Why the Report and Export tabs wait, for an invocation that isn't scheduled yet. */
const NOT_SCHEDULED_YET =
    "This workflow is not currently scheduled. The current state is new. Disabled tabs are available if the workflow is fully scheduled and all jobs have completed.";

/**
 * Waits for the page's header to name the workflow. The tabs follow the workflow the page
 * loads for that header, so checks on them before this would race it.
 */
async function seeWorkflowLoaded({ canvas, step }: PlayContext) {
    await step('See the page for "Test Workflow"', async () => {
        await expect(await canvas.findByText(/^Invoked Workflow: Test Workflow$/)).toBeVisible();
    });
}

/** Sees whether the Report and Export tabs can be opened. */
async function seeReportAndExportTabs({ canvas, step }: PlayContext, open: boolean) {
    await step(
        open ? "See the Report and Export tabs open" : "See the Report and Export tabs unavailable",
        async () => {
            for (const name of ["Report", "Export"]) {
                const tab = canvas.getByRole("link", { name });
                if (open) {
                    await expect(tab).not.toHaveAttribute("aria-disabled");
                } else {
                    await expect(tab).toHaveAttribute("aria-disabled", "true");
                }
            }
        },
    );
}

/**
 * Sees whether the invocation is still running, which offers to cancel it, and whether a Debug tab
 * helps find out why a job failed. `SchedulingNew` and `JobFailed` show each can appear.
 */
async function seeRunningAndDebug({ canvas, step }: PlayContext, running: boolean, debug: boolean) {
    const label = `${running ? "still running" : "finished"}, ${debug ? "with" : "no"} Debug tab`;
    await step(`See it ${label}`, async () => {
        // The tooltip renders inside the button and joins its name (BUGS_FOUND, GButton).
        const cancel = canvas.queryByRole("button", { name: /^Cancel Workflow( |$)/ });
        const debugTab = canvas.queryByRole("link", { name: "Debug" });
        await (running ? expect(cancel).toBeVisible() : expect(cancel).not.toBeInTheDocument());
        await (debug ? expect(debugTab).toBeVisible() : expect(debugTab).not.toBeInTheDocument());
    });
}

/** Fully scheduled and every job done, so every tab is open. */
export const Completed: Story = {
    play: async (context) => {
        await seeWorkflowLoaded(context);
        await seeReportAndExportTabs(context, true);
        await context.step("See no note about unavailable tabs", async () => {
            await expect(context.canvas.queryAllByTitle(/disabled tabs/i)).toHaveLength(0);
        });
        await seeRunningAndDebug(context, false, false);
    },

    // TODO a11y: aria-progressbar-name, label-content-name-mismatch, list (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Not scheduled yet: the page polls the invocation, and the Report and Export tabs wait. */
export const SchedulingNew: Story = {
    parameters: {
        // TODO a11y: aria-progressbar-name, aria-prohibited-attr, label-content-name-mismatch, list (2026-10-10 audit).
        a11y: { test: "todo" },
        msw: { handlers: { invocation: invocation({ state: "new" }) } },
    },
    play: async (context) => {
        await seeWorkflowLoaded(context);
        await seeReportAndExportTabs(context, false);
        await context.step("See a note saying why the tabs wait, on the tabs and on a badge after them", async () => {
            const noted = context.canvas.getAllByTitle(NOT_SCHEDULED_YET);
            await expect(noted.map((element) => element.textContent?.trim())).toEqual(["Report", "Export", ""]);
            const badge = noted[2]!;
            await expect(badge).toBeVisible();
            // The badge is an icon with no name of its own; hovering it shows the note.
            await context.userEvent.hover(badge);
            const tooltip = await within(context.canvasElement.ownerDocument.body).findByRole("tooltip", {
                name: NOT_SCHEDULED_YET,
            });
            await expect(tooltip).toBeVisible();
            await context.userEvent.unhover(badge);
        });
        await seeRunningAndDebug(context, true, false);
    },
};

/** Scheduled, but a job is still running, so only the jobs summary is polled. */
export const JobRunning: Story = {
    parameters: {
        // TODO a11y: aria-progressbar-name, aria-prohibited-attr, label-content-name-mismatch, list (2026-10-10 audit).
        a11y: { test: "todo" },
        msw: { handlers: { jobsSummary: jobsSummary({ ...TERMINAL_JOBS, states: { running: 1 } }) } },
    },
};

/** Scheduled, but Galaxy is still creating its jobs, so the jobs summary is polled. */
export const JobsBeingCreated: Story = {
    parameters: {
        // TODO a11y: aria-progressbar-name, aria-prohibited-attr, label-content-name-mismatch, list (2026-10-10 audit).
        a11y: { test: "todo" },
        msw: { handlers: { jobsSummary: jobsSummary({ ...TERMINAL_JOBS, populated_state: "new" }) } },
    },
};

/** A job failed while another still runs: no Debug tab until everything has finished. */
export const JobFailedWhileAnotherRuns: Story = {
    parameters: {
        // TODO a11y: aria-progressbar-name, aria-prohibited-attr, label-content-name-mismatch, list (2026-10-10 audit).
        a11y: { test: "todo" },
        msw: { handlers: { jobsSummary: jobsSummary({ ...TERMINAL_JOBS, states: { running: 1, error: 1 } }) } },
    },
    play: async (context) => {
        await seeWorkflowLoaded(context);
        await seeRunningAndDebug(context, true, false);
    },
};

/** Finished with a failed job, so the Debug tab helps find out why. */
export const JobFailed: Story = {
    parameters: {
        // TODO a11y: aria-progressbar-name, label-content-name-mismatch, list (2026-10-10 audit).
        a11y: { test: "todo" },
        msw: { handlers: { jobsSummary: jobsSummary({ ...TERMINAL_JOBS, states: { ok: 1, error: 1 } }) } },
    },
    play: async (context) => {
        await seeWorkflowLoaded(context);
        await seeRunningAndDebug(context, false, true);
    },
};

/** The invocation belongs to someone else. */
export const LoadFailed: Story = {
    parameters: {
        msw: {
            handlers: {
                invocation: http.get("/api/invocations/{invocation_id}", ({ response }) =>
                    response.untyped(
                        HttpResponse.json(
                            { err_msg: "User does not own specified item.", err_code: 403002 },
                            { status: 403 },
                        ),
                    ),
                ),
            },
        },
    },
    play: async ({ canvas, step }) => {
        await step("See the server's error, and no invocation page", async () => {
            // Pre-existing bug, tolerated here: the alert interpolates the stored error object,
            // so it reads "Error: User does not own specified item." (BUGS_FOUND).
            await expect(await canvas.findByRole("alert")).toHaveTextContent(
                /^(Error: )?User does not own specified item\.$/,
            );
            await expect(canvas.queryByRole("link", { name: "Overview" })).not.toBeInTheDocument();
        });
    },
};
