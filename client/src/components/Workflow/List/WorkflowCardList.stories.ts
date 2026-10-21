import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { seeToasts, withToasts } from "@tests/test-data/toasts";
import { getFakeWorkflowSummary } from "@tests/test-data/workflows";
import { HttpResponse } from "msw";
import { expect, waitFor, within } from "storybook/test";

import { http } from "@/api/client/__mocks__/http";
import { OWN_WORKFLOW_RUNS, SIGNED_IN_USER } from "@/components/Workflow/test_fixtures";

import WorkflowCardList from "./WorkflowCardList.vue";

const RNA_SEQ = getFakeWorkflowSummary({
    id: "f2db41e1fa331b3e",
    name: "RNA-seq: align paired-end reads and count genes",
    owner: SIGNED_IN_USER.username,
    annotations: ["Aligns paired-end reads to hg38 with HISAT2 and counts reads per gene."],
    tags: ["rna-seq", "name:hg38"],
});

const VARIANT_CALLING = getFakeWorkflowSummary({
    id: "a799d38679e985db",
    name: "Variant calling with FreeBayes",
    owner: SIGNED_IN_USER.username,
    update_time: "2026-09-14T08:30:00",
});

const PUBLISHED_WORKFLOWS = [
    getFakeWorkflowSummary({
        id: "33b43b4e7093c91f",
        name: "Genome assembly with Flye",
        owner: "bob",
        published: true,
        importable: true,
        annotations: ["Assembles long Nanopore reads and polishes the assembly with Medaka."],
        tags: ["assembly"],
    }),
    getFakeWorkflowSummary({
        id: "5969b1f7201f12ae",
        name: "16S rRNA amplicon analysis",
        owner: "carol",
        published: true,
        importable: true,
    }),
];

/** How often the user has run each workflow, by invocation state; one they never ran has no counts. */
const RUN_COUNTS: Record<string, Record<string, number>> = { [RNA_SEQ.id]: OWN_WORKFLOW_RUNS };

/** Saves a workflow's new name and answers the workflow under it. */
const renameWorkflow = http.untyped.put("/api/workflows/:workflowId", async ({ params, request }) => {
    const { name } = (await request.json()) as { name: string };
    const workflow = [RNA_SEQ, VARIANT_CALLING].find((w) => w.id === params.workflowId);
    return HttpResponse.json({ ...workflow, name });
});

/** Workflow cards, as on the workflow lists and in the workflow panel, with the rename and preview dialogs they open. */
const meta = {
    title: "Workflow/List/WorkflowCardList",
    component: WorkflowCardList,
    decorators: [withCurrentUser(() => SIGNED_IN_USER)],
    args: { workflows: [RNA_SEQ, VARIANT_CALLING] },
    parameters: {
        msw: {
            handlers: {
                runCounts: http.get("/api/workflows/{workflow_id}/counts", ({ params, response }) =>
                    response(200).json(RUN_COUNTS[params.workflow_id] ?? {}),
                ),
                renameWorkflow,
            },
        },
    },
} satisfies Meta<typeof WorkflowCardList>;

export default meta;
type Story = StoryObj<typeof meta>;

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/**
 * No rename dialog in the page, open or closed. A closed `<dialog>` is hidden from role queries, so
 * this looks for the rename dialog's heading among hidden elements too.
 */
async function seeNoRenameDialog({ canvas }: PlayContext) {
    await expect(canvas.queryByRole("heading", { name: /^Rename Workflow/, hidden: true })).not.toBeInTheDocument();
}

/** Each card's rename button, in card order, once the cards show; checks no rename dialog is open. */
async function seeRenameButtons(context: PlayContext) {
    const { canvas, step } = context;
    let buttons!: HTMLElement[];
    await step("See a rename button on each card and no rename dialog", async () => {
        buttons = await canvas.findAllByRole("button", { name: "Rename" });
        await seeNoRenameDialog(context);
        await expect(buttons).toHaveLength(2);
    });
    return buttons;
}

/**
 * Clicks a card's rename button and sees the dialog ask to rename `name`, with `name` filled in and
 * Rename unavailable until it changes. Returns the dialog.
 */
async function openRename({ canvas, step, userEvent }: PlayContext, button: HTMLElement, name: string) {
    let dialog!: HTMLElement;
    await step(`Rename "${name}"; see the dialog ask for its new name`, async () => {
        await userEvent.click(button);
        dialog = await canvas.findByRole("dialog");
        await expect(within(dialog).getByRole("heading", { name: `Rename Workflow: ${name}` })).toBeVisible();
        await expect(within(dialog).getByRole("textbox")).toHaveValue(name);
        await expect(within(dialog).getByRole("button", { name: "Rename" })).toHaveAttribute("aria-disabled", "true");
    });
    return dialog;
}

/** The user's own workflows, one per row: one run twelve times, one never run. */
export const OwnWorkflows: Story = {};

/** A card's rename button asks for the workflow's new name, starting from its current one. */
export const AsksForNewName: Story = {
    play: async (context) => {
        const [renameFirst] = await seeRenameButtons(context);
        await openRename(context, renameFirst!, RNA_SEQ.name);
    },
};

/** Cancelling one rename and starting another asks about the second workflow, not the first. */
export const AsksAboutEachWorkflowInTurn: Story = {
    play: async (context) => {
        const [renameFirst, renameSecond] = await seeRenameButtons(context);
        const dialog = await openRename(context, renameFirst!, RNA_SEQ.name);
        await context.step("Cancel; the dialog closes", async () => {
            await context.userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
            await waitFor(() => seeNoRenameDialog(context));
        });
        await openRename(context, renameSecond!, VARIANT_CALLING.name);
    },
};

/** Saving a new name closes the dialog and says the workflow was renamed. */
export const RenamesWorkflow: Story = {
    decorators: [withToasts],
    play: async (context) => {
        const { canvas, step, userEvent } = context;
        const [, renameSecond] = await seeRenameButtons(context);
        const dialog = await openRename(context, renameSecond!, VARIANT_CALLING.name);
        const input = within(dialog).getByRole("textbox");
        const rename = within(dialog).getByRole("button", { name: "Rename" });
        await step('Type "Renamed Workflow"; Rename becomes available', async () => {
            await userEvent.clear(input);
            await userEvent.type(input, "Renamed Workflow");
            await expect(rename).not.toHaveAttribute("aria-disabled");
        });
        await step("Rename; see it confirmed and the dialog closed", async () => {
            await userEvent.click(rename);
            await seeToasts(canvas, [["Success", "Workflow renamed"]]);
            await seeNoRenameDialog(context);
        });
    },
};

/** The same workflows as a grid of cards. */
export const GridView: Story = { args: { gridView: true } };

/** Workflows other users published, as the published list shows them. */
export const Published: Story = { args: { workflows: PUBLISHED_WORKFLOWS, publishedView: true } };
