import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentHistory } from "@tests/test-data/currentHistory";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { exactly } from "@tests/test-data/text";
import { formatDistanceToNow } from "date-fns";
import { HttpResponse } from "msw";
import { expect, screen } from "storybook/test";

import { http } from "@/api/client/__mocks__/http";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import { INVOCATION } from "@/components/WorkflowInvocationState/test_fixtures";
import { escapeRegExp } from "@/utils/regExp";

import {
    INVOCATION_HISTORY,
    OWN_WORKFLOW,
    OWN_WORKFLOW_RUNS,
    PUBLISHED_WORKFLOW,
    SIGNED_IN_USER,
} from "./test_fixtures";

import WorkflowAnnotation from "./WorkflowAnnotation.vue";

/** Answers the workflow instance the annotation describes with `storedWorkflow`. */
function workflow(storedWorkflow: StoredWorkflowDetailed) {
    return http.get("/api/workflows/{workflow_id}", ({ response }) =>
        response.untyped(HttpResponse.json(storedWorkflow)),
    );
}

/**
 * The line under a workflow's name on its run form and on an invocation's page: when it was edited
 * or invoked, the history it ran in, and who published it or how often the user has run it.
 */
const meta = {
    title: "Workflow/WorkflowAnnotation",
    component: WorkflowAnnotation,
    decorators: [withCurrentUser(() => SIGNED_IN_USER), withCurrentHistory(INVOCATION_HISTORY)],
    args: { workflowId: INVOCATION.workflow_id, historyId: INVOCATION.history_id },
    parameters: {
        msw: {
            handlers: {
                workflow: workflow(OWN_WORKFLOW),
                runCount: http.get("/api/workflows/{workflow_id}/counts", ({ response }) =>
                    response(200).json(OWN_WORKFLOW_RUNS),
                ),
            },
        },
    },
} satisfies Meta<typeof WorkflowAnnotation>;

export default meta;
type Story = StoryObj<typeof meta>;

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/** The stories' Galaxy times, which carry no zone, as the UTC instants the dates' titles show. */
const EDITED_AT = "2026-08-31T10:00:00.000Z";
const INVOKED_AT = "2021-01-04T17:40:58.407Z";

/** Reads how long ago the workflow was edited or invoked; the full time is the date's title. */
async function seeTimeSince({ canvas, step }: PlayContext, what: "edited" | "invoked", at: string) {
    await step(`See when the workflow was ${what}`, async () => {
        const date = await canvas.findByTitle(at, {}, { timeout: 5000 });
        const elapsed = formatDistanceToNow(new Date(at), { addSuffix: true });
        await expect(date).toHaveTextContent(exactly(elapsed));
        await expect(date.parentElement).toHaveTextContent(exactly(`${what} ${elapsed}`));
        await expect(date).toBeVisible();
    });
}

/** Reads the user's run count, which links to the workflow's runs, and finds no publisher badge. */
async function seeRunCount({ canvas, step }: PlayContext) {
    await step("See how often the user has run their workflow, linking to its runs", async () => {
        // Found by text: `v-g-tooltip` names the link with its tooltip (BUGS_FOUND).
        // The count has its own request, sent once the workflow has loaded.
        const count = await canvas.findByText(`workflow runs: ${OWN_WORKFLOW_RUNS.scheduled}`, {}, { timeout: 5000 });
        await expect(count).toBeVisible();
        await expect(count.closest("a")).toHaveAttribute("href", `/workflows/${OWN_WORKFLOW.id}/invocations`);
    });
    await step("See no badge naming who published it", async () => {
        await expect(canvas.queryByText(OWN_WORKFLOW.owner)).not.toBeInTheDocument();
    });
}

/** Hovers the publisher's badge to read who published the workflow, and finds no run count. */
async function seePublisher({ canvas, step, userEvent }: PlayContext) {
    await step(`See the workflow was published by "${PUBLISHED_WORKFLOW.owner}"`, async () => {
        const owner = await canvas.findByText(PUBLISHED_WORKFLOW.owner, {}, { timeout: 5000 });
        // The badge holds the owner's name beside its icon.
        const badge = owner.parentElement!;
        await expect(badge).toHaveTextContent(exactly(PUBLISHED_WORKFLOW.owner));
        await expect(badge).toBeVisible();
        const tooltip = { name: `Published by '${PUBLISHED_WORKFLOW.owner}'` };
        await expect(screen.queryByRole("tooltip", tooltip)).not.toBeInTheDocument();
        await userEvent.hover(badge);
        await expect(await screen.findByRole("tooltip", tooltip)).toHaveTextContent(exactly(tooltip.name));
        await userEvent.unhover(badge);
        await expect(screen.queryByRole("tooltip", tooltip)).not.toBeInTheDocument();
    });
    await step("See no run count", async () => {
        await expect(canvas.queryByText(/workflow runs|never run/)).not.toBeInTheDocument();
    });
}

/** Running the user's own workflow: when it was edited, its description and how often it has run. */
export const RunForm: Story = {
    args: { showDetails: true },
    play: async (context) => {
        await seeTimeSince(context, "edited", EDITED_AT);
        const { canvas, step } = context;
        await step("See the workflow's description", async () => {
            await expect(canvas.getByText(exactly(OWN_WORKFLOW.annotation!))).toBeVisible();
        });
        await step("See no history the run would go to", async () => {
            await expect(canvas.queryByText("History:")).not.toBeInTheDocument();
            await expect(canvas.queryByText(INVOCATION_HISTORY.name)).not.toBeInTheDocument();
        });
        await seeRunCount(context);
    },

    // TODO a11y: label-content-name-mismatch (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** An invocation of the user's own workflow, in their current history. */
export const Invocation: Story = {
    args: { invocationCreateTime: INVOCATION.create_time },
    play: async (context) => {
        await seeTimeSince(context, "invoked", INVOKED_AT);
        const { canvas, step } = context;
        await step("See the history it ran in, marked as the current one", async () => {
            await expect(canvas.getByText("History:")).toBeVisible();
            // The link's tooltip text joins its name (BUGS_FOUND), so the name is matched from the start.
            const link = await canvas.findByRole("button", {
                name: new RegExp(`^${escapeRegExp(INVOCATION_HISTORY.name)}\\b`),
            });
            await expect(link).toBeVisible();
            await expect(canvas.getByText("(current)")).toBeVisible();
            await expect(canvas.queryByText("(not current)")).not.toBeInTheDocument();
        });
        await step("See no workflow description", async () => {
            await expect(canvas.queryByText(exactly(OWN_WORKFLOW.annotation!))).not.toBeInTheDocument();
        });
        await seeRunCount(context);
    },

    // TODO a11y: label-content-name-mismatch (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Running a workflow another user published: who published it, and no run count. */
export const PublishedRunForm: Story = {
    args: { showDetails: true },
    parameters: { msw: { handlers: { workflow: workflow(PUBLISHED_WORKFLOW) } } },
    play: seePublisher,
};

/** An invocation of a workflow another user published. */
export const PublishedInvocation: Story = {
    args: { invocationCreateTime: INVOCATION.create_time },
    parameters: { msw: { handlers: { workflow: workflow(PUBLISHED_WORKFLOW) } } },
    play: seePublisher,
};
