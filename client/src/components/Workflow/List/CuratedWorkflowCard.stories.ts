import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeAnonymousUser } from "@tests/test-data";
import { viewedBy, withCurrentUser } from "@tests/test-data/currentUser";
import { withToasts } from "@tests/test-data/toasts";
import { getFakeWorkflowSummary } from "@tests/test-data/workflows";
import { HttpResponse } from "msw";

import { http } from "@/api/client/__mocks__/http";
import type { CuratedWorkflow } from "@/api/curatedWorkflows";
import { SIGNED_IN_USER } from "@/components/Workflow/test_fixtures";

import CuratedWorkflowCard from "./CuratedWorkflowCard.vue";

const VELOCYTO_TRS =
    "https://dockstore.org/api/ga4gh/trs/v2/tools/%23workflow%2Fgithub.com%2Fiwc-workflows%2Fvelocyto%2Fmain/versions";

/** An IWC catalog row, pinned to its release on Dockstore with the branch as fallback. */
const VELOCYTO: CuratedWorkflow = {
    id: "velocyto-velocyto-on10x-filtered-barcodes",
    name: "Velocyto on 10x filtered barcodes",
    description: "A curated single cell workflow",
    tags: ["single-cell"],
    collections: ["Single Cell"],
    number_of_steps: 5,
    update_time: "2026-01-01T00:00:00",
    release: "0.1",
    doi: "10.5281/zenodo.1234567",
    external_url: "https://iwc.galaxyproject.org/workflow/velocyto-velocyto-on10x-filtered-barcodes/",
    owner: null,
    stored_workflow_id: null,
    trs_url: `${VELOCYTO_TRS}/v0.1`,
    trs_fallback_url: `${VELOCYTO_TRS}/main`,
    missing_tools: [],
};

/** A workflow a curator published on this Galaxy; the server doesn't check its tools. */
const HOSTED_WORKFLOW: CuratedWorkflow = {
    ...VELOCYTO,
    id: "f2db41e1fa331b3e",
    name: "Locally curated workflow",
    collections: [],
    stored_workflow_id: "f2db41e1fa331b3e",
    owner: "curator",
    external_url: null,
    doi: null,
    release: null,
    trs_url: null,
    trs_fallback_url: null,
    missing_tools: null,
};

/** Galaxy imports a TRS URL by fetching its descriptor from the TRS server, which answers each URL with `answer`. */
function trsImport(answer: (trsUrl: string) => "imported" | "not on server" | "unreachable") {
    return http.untyped.post("/api/workflows", async ({ request }) => {
        const { trs_url } = (await request.json()) as { trs_url: string };
        // Galaxy names the server: the part of the TRS URL before its tools path.
        const server = trs_url.split("/ga4gh/trs/v2/tools")[0];
        switch (answer(trs_url)) {
            case "imported":
                return HttpResponse.json({
                    id: "a799d38679e985db",
                    message: `Workflow '${VELOCYTO.name}' imported successfully.`,
                    status: "success",
                });
            case "not on server":
                return HttpResponse.json(
                    { err_msg: `TRS server ${server} responded with HTTP 404.`, err_code: 404001 },
                    { status: 404 },
                );
            case "unreachable":
                return HttpResponse.json(
                    { err_msg: `TRS server ${server} could not be reached.`, err_code: 502001 },
                    { status: 502 },
                );
        }
    });
}

/** Copying a hosted workflow downloads it, then saves it as the user's own. */
const copyHostedWorkflow = [
    http.untyped.get("/api/workflows/:workflowId/download", () =>
        HttpResponse.json({ name: HOSTED_WORKFLOW.name, a_galaxy_workflow: "true", steps: {} }),
    ),
    http.untyped.post("/api/workflows", async ({ request }) => {
        const { workflow } = (await request.json()) as { workflow: { name: string } };
        return HttpResponse.json(
            getFakeWorkflowSummary({ id: "a799d38679e985db", name: workflow.name, owner: SIGNED_IN_USER.username }),
        );
    }),
];

/** A card on the curated workflows list (IWC's catalog or this Galaxy's own picks). */
const meta = {
    title: "Workflow/List/CuratedWorkflowCard",
    component: CuratedWorkflowCard,
    decorators: [withToasts, withCurrentUser(() => SIGNED_IN_USER)],
    args: { workflow: VELOCYTO },
    parameters: { msw: { handlers: { workflowImport: trsImport(() => "imported") } } },
} satisfies Meta<typeof CuratedWorkflowCard>;

export default meta;
type Story = StoryObj<typeof meta>;

/** An IWC workflow whose tools are all installed here; Import fetches its release from Dockstore. */
export const CatalogWorkflow: Story = {};

/** Dockstore hasn't synced the release tag yet, so Import falls back to the branch. */
export const ReleaseNotOnDockstoreYet: Story = {
    parameters: {
        msw: {
            handlers: {
                workflowImport: trsImport((trsUrl) => (trsUrl === VELOCYTO.trs_url ? "not on server" : "imported")),
            },
        },
    },
};

/** No release to pin, and the branch isn't on Dockstore either; Import reports the failure. */
export const NotOnDockstore: Story = {
    args: { workflow: { ...VELOCYTO, release: null, trs_url: `${VELOCYTO_TRS}/main`, trs_fallback_url: null } },
    parameters: { msw: { handlers: { workflowImport: trsImport(() => "not on server") } } },
};

/** Dockstore is down; Import reports it rather than trying the branch. */
export const DockstoreUnreachable: Story = {
    parameters: { msw: { handlers: { workflowImport: trsImport(() => "unreachable") } } },
};

/** The catalog gave nothing to import from: Import is disabled. */
export const NotImportable: Story = {
    args: { workflow: { ...VELOCYTO, trs_url: null, trs_fallback_url: null } },
};

/** Anonymous visitors are asked to log in before importing. */
export const Anonymous: Story = {
    parameters: viewedBy(getFakeAnonymousUser()),
};

/** Three of the workflow's tools aren't installed here. */
export const NeedsTools: Story = {
    args: {
        workflow: {
            ...VELOCYTO,
            missing_tools: [
                "toolshed.g2.bx.psu.edu/repos/iuc/fastp/fastp/0.23.4+galaxy0",
                "toolshed.g2.bx.psu.edu/repos/iuc/multiqc/multiqc/1.11+galaxy1",
                "wig_to_bigWig",
            ],
        },
    },
};

/** One tool isn't installed here; an admin can still import the workflow and install it. */
export const NeedsOneTool: Story = {
    args: { workflow: { ...VELOCYTO, missing_tools: ["wig_to_bigWig"] } },
};

/** Published on this Galaxy: Run and View it here, or Import a copy of your own. */
export const HostedHere: Story = {
    args: { workflow: HOSTED_WORKFLOW },
    parameters: { msw: { handlers: { workflowImport: copyHostedWorkflow } } },
};
