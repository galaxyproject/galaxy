import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { getFakeWorkflowSummary } from "@tests/test-data/workflows";
import { HttpResponse } from "msw";

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

/** The user's own workflows, one per row: one run twelve times, one never run. */
export const OwnWorkflows: Story = {};

/** The same workflows as a grid of cards. */
export const GridView: Story = { args: { gridView: true } };

/** Workflows other users published, as the published list shows them. */
export const Published: Story = { args: { workflows: PUBLISHED_WORKFLOWS, publishedView: true } };
