import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeAnonymousUser } from "@tests/test-data";
import { viewedBy, withCurrentUser } from "@tests/test-data/currentUser";
import { NOTIFICATIONS, seeToasts, withToasts } from "@tests/test-data/toasts";
import { getFakeWorkflowSummary } from "@tests/test-data/workflows";
import { HttpResponse } from "msw";
import { expect, waitFor, within } from "storybook/test";

import { http } from "@/api/client/__mocks__/http";
import type { CuratedWorkflow } from "@/api/curatedWorkflows";
import { SIGNED_IN_USER } from "@/components/Workflow/test_fixtures";
import { escapeRegExp } from "@/utils/regExp";

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
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

const MORE_OPTIONS = "More options";

/** A link or menu item as a user reads it: its name, where it goes, and whether in a new tab. */
type Destination = [name: string, href: string, newTab: boolean];

function destinationOf(element: HTMLElement): Destination {
    return [
        element.textContent?.trim() ?? "",
        element.getAttribute("href") ?? "",
        element.getAttribute("target") === "_blank",
    ];
}

/** Waits for the card titled `name`, plain text with no link to a preview. */
async function seeCard({ canvas, step }: PlayContext, name: string) {
    await step(`See the card titled "${name}"`, async () => {
        const heading = await canvas.findByRole("heading", { name }, { timeout: 5000 });
        await expect(heading).toBeVisible();
        await expect(within(heading).queryByRole("link")).not.toBeInTheDocument();
    });
}

/**
 * Reads the card's links and buttons in order, then opens "More options" to read its items, and
 * closes it again, so the story still shows its initial state.
 */
async function seeActions(
    { canvas, step, userEvent }: PlayContext,
    { links, buttons, menuItems }: { links: Destination[]; buttons: string[]; menuItems: Destination[] },
) {
    await step(`See the actions: ${[...links.map(([name]) => name), ...buttons].join(", ")}`, async () => {
        await expect(canvas.queryAllByRole("link").map(destinationOf)).toEqual(links);
        await expect(canvas.getAllByRole("button")).toEqual(
            buttons.map((name) => canvas.getByRole("button", { name })),
        );
    });
    await step(`Open "${MORE_OPTIONS}": ${menuItems.map(([name]) => name).join(", ")}; then close it`, async () => {
        const toggle = canvas.getByRole("button", { name: MORE_OPTIONS });
        await userEvent.click(toggle);
        const menu = await canvas.findByRole("menu", { name: MORE_OPTIONS });
        await expect(menu).toBeVisible();
        await expect(within(menu).getAllByRole("menuitem").map(destinationOf)).toEqual(menuItems);
        await userEvent.click(toggle);
        await userEvent.unhover(toggle);
        await waitFor(() => expect(canvas.queryByRole("menu")).not.toBeInTheDocument());
    });
}

/** Sees Import enabled or disabled, described by `why`. */
async function seeImport({ canvas, step }: PlayContext, enabled: boolean, why: string) {
    await step(`See Import ${enabled ? "enabled" : "disabled"}: "${why}"`, async () => {
        const importButton = canvas.getByRole("button", { name: "Import" });
        if (enabled) {
            await expect(importButton).not.toHaveAttribute("aria-disabled", "true");
        } else {
            await expect(importButton).toHaveAttribute("aria-disabled", "true");
        }
        await expect(importButton).toHaveAccessibleDescription(why);
    });
}

/**
 * Sees whether the workflow can run here: its ready badge or missing-tools footer note and description,
 * or neither when the server did not check.
 */
async function seeRunnability({ canvas, step }: PlayContext, badge: [label: string, why: string] | null) {
    await step(badge ? `See the "${badge[0]}" badge: "${badge[1]}"` : "See no runnability badge", async () => {
        const shown = canvas.queryAllByText(/^(Ready to run|Needs \d+ tools?)$/);
        await expect(shown.map((element) => element.textContent?.trim())).toEqual(badge ? [badge[0]] : []);
        if (badge) {
            await expect(shown[0]).toBeVisible();
            // Missing tools are a footer detail whose list item owns the description.
            const described = shown[0]!.closest<HTMLElement>('[id^="g-card-badge-curated-missing-tools-"]') ?? shown[0];
            await expect(described).toHaveAccessibleDescription(badge[1]);
        }
    });
}

/**
 * A failed import's toast for `error`. The component interpolates the `ApiError`, whose `toString()`
 * adds an "Error: " prefix; accept the message with and without it, so dropping it doesn't fail this.
 */
function failedImport(error: string): [label: string, toast: RegExp] {
    return [
        `"Failed to import workflow: ${error}"`,
        new RegExp(`^Error Failed to import workflow: (Error: )?${escapeRegExp(error)}$`),
    ];
}

/**
 * Clicks Import and sees the one toast that reports the result, its title and message matching
 * `toast`. (`seeToasts` takes exact text only, and a failure toast has to tolerate a known bug.)
 */
async function importAndSee({ canvas, step, userEvent }: PlayContext, [label, toast]: [string, RegExp]) {
    await step(`Import: see the toast ${label}`, async () => {
        await seeToasts(canvas, []);
        await userEvent.click(canvas.getByRole("button", { name: "Import" }));
        const notifications = within(canvas.getByRole("region", { name: NOTIFICATIONS }));
        // Toasts dismiss themselves after 3s, so wait a little longer than the default, but not that long.
        await waitFor(() => expect(notifications.queryAllByRole("alert")).toHaveLength(1), { timeout: 2500 });
        await expect(notifications.getByRole("alert")).toHaveTextContent(toast);
    });
}

/** An IWC workflow whose tools are all installed here; Import fetches its release from Dockstore. */
export const CatalogWorkflow: Story = {
    play: async (context) => {
        await seeCard(context, VELOCYTO.name);
        await seeRunnability(context, ["Ready to run", "Every tool this workflow uses is installed on this Galaxy"]);
        await seeActions(context, {
            links: [["IWC", VELOCYTO.external_url!, true]],
            buttons: ["Single Cell", MORE_OPTIONS, "Import"],
            menuItems: [["View DOI", `https://doi.org/${VELOCYTO.doi}`, true]],
        });
        await seeImport(context, true, "Import this workflow into your account");
        await context.step("See steps and version in the card footer", async () => {
            const steps = context.canvas.getByText("5 steps");
            const version = context.canvas.getByText("v0.1");
            const footer = context.canvasElement.querySelector(`#g-card-${VELOCYTO.id}-details`);
            await expect(steps).toBeVisible();
            await expect(version).toBeVisible();
            await expect(footer).toContainElement(steps);
            await expect(footer).toContainElement(version);
        });
    },
};

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

/** Importing a branch Dockstore doesn't have says which server answered 404. */
export const ReportsMissingBranch: Story = {
    ...NotOnDockstore,
    play: async (context) => {
        await seeCard(context, VELOCYTO.name);
        await importAndSee(context, failedImport("TRS server https://dockstore.org/api responded with HTTP 404."));
    },
};

/** Dockstore is down; Import reports it rather than trying the branch. */
export const DockstoreUnreachable: Story = {
    parameters: { msw: { handlers: { workflowImport: trsImport(() => "unreachable") } } },
};

/** Importing while Dockstore is down says the server couldn't be reached. */
export const ReportsUnreachableDockstore: Story = {
    ...DockstoreUnreachable,
    play: async (context) => {
        await seeCard(context, VELOCYTO.name);
        await importAndSee(context, failedImport("TRS server https://dockstore.org/api could not be reached."));
    },
};

/** The catalog gave nothing to import from: Import is disabled. */
export const NotImportable: Story = {
    args: { workflow: { ...VELOCYTO, trs_url: null, trs_fallback_url: null } },
    play: async (context) => {
        await seeCard(context, VELOCYTO.name);
        await seeImport(context, false, "This workflow cannot be imported automatically");
    },
};

/** Anonymous visitors are asked to log in before importing. */
export const Anonymous: Story = {
    parameters: viewedBy(getFakeAnonymousUser()),
    play: async (context) => {
        await seeCard(context, VELOCYTO.name);
        await seeImport(context, false, "Log in to import this workflow");
    },
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
    play: async (context) => {
        await seeCard(context, VELOCYTO.name);
        await seeRunnability(context, ["Needs 3 tools", "Not installed on this Galaxy: fastp, multiqc, wig_to_bigWig"]);
    },
};

/** One tool isn't installed here; an admin can still import the workflow and install it. */
export const NeedsOneTool: Story = {
    args: { workflow: { ...VELOCYTO, missing_tools: ["wig_to_bigWig"] } },
    play: async (context) => {
        await seeCard(context, VELOCYTO.name);
        await seeRunnability(context, ["Needs 1 tool", "Not installed on this Galaxy: wig_to_bigWig"]);
        await seeImport(context, true, "Import this workflow into your account");
    },
};

/** Published on this Galaxy: Run and View it here, or Import a copy of your own. */
export const HostedHere: Story = {
    args: { workflow: HOSTED_WORKFLOW },
    parameters: { msw: { handlers: { workflowImport: copyHostedWorkflow } } },
    play: async (context) => {
        await seeCard(context, HOSTED_WORKFLOW.name);
        await seeRunnability(context, null);
        await seeActions(context, {
            links: [["Run", `/workflows/run?id=${HOSTED_WORKFLOW.stored_workflow_id}`, false]],
            buttons: [MORE_OPTIONS, "Import"],
            menuItems: [["View workflow", `/published/workflow?id=${HOSTED_WORKFLOW.stored_workflow_id}`, false]],
        });
    },
};

/** Importing a workflow hosted here copies it into the user's own workflows. */
export const CopiesHostedWorkflow: Story = {
    ...HostedHere,
    play: async (context) => {
        await seeCard(context, HOSTED_WORKFLOW.name);
        await importAndSee(context, [`"Workflow imported successfully"`, /^Success Workflow imported successfully$/]);
    },
};
