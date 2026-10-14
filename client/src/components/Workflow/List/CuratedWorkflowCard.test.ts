import { composeStories } from "@storybook/vue3-vite";
import { deferred } from "@tests/vitest/deferred";
import { createTestRouter, nth } from "@tests/vitest/helpers";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { nextTick } from "vue";

import type { CuratedWorkflow } from "@/api/curatedWorkflows";
import { Services } from "@/components/Workflow/services";
import { copyWorkflow } from "@/components/Workflow/workflows.services";
import { Toast } from "@/composables/toast";
import { useConfigStore } from "@/stores/configurationStore";
import { ensureDefined } from "@/utils/assertions";

import * as CuratedWorkflowCardStories from "./CuratedWorkflowCard.stories";

import CuratedWorkflowCard from "./CuratedWorkflowCard.vue";
import GCard from "@/components/Common/GCard.vue";

// Spied, not replaced: imports still reach the story's handlers.
const importTrsToolFromUrl = vi.spyOn(Services.prototype, "importTrsToolFromUrl");
vi.mock("@/components/Workflow/workflows.services", { spy: true });

vi.mock("@/components/Workflow/redirectPath", () => ({
    getRedirectOnImportPath: () => "/workflows/list",
}));

const stories = composeStories(CuratedWorkflowCardStories);
const mountStory = useStoryMount();

const toastError = vi.spyOn(Toast, "error");
let routerPush: ReturnType<typeof vi.spyOn>;

const CATALOG_WORKFLOW = ensureDefined(stories.CatalogWorkflow.args.workflow);
const PINNED_TRS_URL = CATALOG_WORKFLOW.trs_url;
const BRANCH_TRS_URL = CATALOG_WORKFLOW.trs_fallback_url;

type CardStory = StoryOf<typeof stories>;

function mountCard(
    story: CardStory,
    props: { workflow?: CuratedWorkflow; gridView?: boolean; installationRequested?: boolean } = {},
) {
    const router = createTestRouter();
    // Stubbed so the assertions can see navigation; a real push would also
    // warn about redundant routes across repeated mounts.
    routerPush = vi.spyOn(router, "push").mockResolvedValue(undefined);
    return mountStory(story, { router, props });
}

function workflowOf(story: CardStory): CuratedWorkflow {
    return ensureDefined(story.args.workflow);
}

function iwcWorkflow(overrides: Partial<CuratedWorkflow> = {}): CuratedWorkflow {
    return { ...CATALOG_WORKFLOW, ...overrides };
}

function localWorkflow(overrides: Partial<CuratedWorkflow> = {}): CuratedWorkflow {
    return { ...workflowOf(stories.HostedHere), ...overrides };
}

function mountWorkflowCard(
    workflow: CuratedWorkflow,
    isAnonymous = false,
    props: { gridView?: boolean; installationRequested?: boolean } = {},
) {
    return mountCard(isAnonymous ? stories.Anonymous : stories.CatalogWorkflow, { workflow, ...props });
}

async function mountRequestCard(
    workflow: CuratedWorkflow,
    isAnonymous = false,
    props: { installationRequested?: boolean } = {},
    enabled = true,
) {
    const wrapper = mountWorkflowCard(workflow, isAnonymous, props);
    await flushPromises();
    useConfigStore().setConfiguration({
        enable_notification_system: true,
        enable_tool_installation_request_form: enabled,
    });
    await nextTick();
    return wrapper;
}

function importActionOf(wrapper: ReturnType<typeof mountCard>) {
    const action = ensureDefined(
        ensureDefined(wrapper.getComponent(GCard).props("primaryActions")).find(
            (action) => action.id === "curated-import",
        ),
    );
    return { ...action, handler: ensureDefined(action.handler) };
}

async function clickImport(wrapper: ReturnType<typeof mountCard>, workflow: CuratedWorkflow) {
    await wrapper.get(`#g-card-action-curated-import-${workflow.id}`).trigger("click");
    await flushPromises();
}

function badgeById(wrapper: ReturnType<typeof mountCard>, id: string) {
    const badges = wrapper.getComponent(GCard).props("badges") ?? [];
    return badges.find((badge) => badge.id === id);
}

function missingToolsOf(wrapper: ReturnType<typeof mountCard>, workflow: CuratedWorkflow) {
    return wrapper.find(`#g-card-badge-curated-missing-tools-${workflow.id}`);
}

function extraActionById(wrapper: ReturnType<typeof mountCard>, id: string) {
    const action = (wrapper.findComponent(GCard).props("extraActions") ?? []).find((extra) => extra.id === id);
    if (!action) {
        throw new Error(`No "${id}" action in the card menu`);
    }
    return action;
}

function actionIds(wrapper: ReturnType<typeof mountCard>): string[] {
    const card = wrapper.getComponent(GCard);
    const actions = [
        ...(card.props("primaryActions") ?? []),
        ...(card.props("secondaryActions") ?? []),
        ...(card.props("extraActions") ?? []),
    ];
    return actions.map((action) => action.id);
}

describe("CuratedWorkflowCard", () => {
    beforeEach(() => {
        importTrsToolFromUrl.mockReset();
        vi.mocked(copyWorkflow).mockReset();
        toastError.mockClear();
    });

    it("renders the title as plain text with no preview link", () => {
        // A catalog row's id is an IWC slug, so a preview modal keyed on it would 404.
        const wrapper = mountCard(stories.CatalogWorkflow);
        const title = wrapper.get(`#g-card-title-${CATALOG_WORKFLOW.id}`);

        expect(title.text()).toContain("Velocyto on 10x filtered barcodes");
        expect(wrapper.find(`#g-card-title-link-${CATALOG_WORKFLOW.id}`).exists()).toBe(false);
        expect(title.find("a").exists()).toBe(false);
    });

    it("marks the card so Selenium's workflow-card count is unaffected", () => {
        const card = mountCard(stories.CatalogWorkflow).getComponent(CuratedWorkflowCard);

        expect(card.classes()).toContain("curated-workflow-card");
        expect(card.classes()).not.toContain("workflow-card");
    });

    it("keeps the IWC link out of the overflow menu", () => {
        const card = mountWorkflowCard(iwcWorkflow()).findComponent(GCard);
        const ids = (props: "secondaryActions" | "extraActions") =>
            (card.props(props) ?? []).map((action: { id: string }) => action.id);

        expect(ids("secondaryActions")).toEqual(["curated-external-link"]);
        expect(ids("extraActions")).toEqual(["curated-doi"]);
    });

    it("keeps only runnability beside the title and moves steps and version to the footer", () => {
        const workflow = iwcWorkflow();
        const wrapper = mountWorkflowCard(workflow);

        const titleRowIds = (wrapper.findComponent(GCard).props("badges") ?? []).map(
            (badge: { id: string }) => badge.id,
        );
        expect(titleRowIds).toEqual(["curated-runnable"]);

        const details = wrapper.find(`#g-card-${workflow.id}-details`);
        expect(details.find(`#g-card-badge-curated-steps-${workflow.id}`).text()).toBe("5 steps");
        expect(details.find(`#g-card-badge-curated-release-${workflow.id}`).text()).toBe("v0.1");
    });

    it("leaves the colored tags to list view", () => {
        const workflow = iwcWorkflow();

        expect(mountWorkflowCard(workflow, false, { gridView: true }).findComponent(GCard).props("tags")).toEqual([]);
        expect(mountWorkflowCard(workflow).findComponent(GCard).props("tags")).toEqual(workflow.tags);
    });

    it("clamps the description to plain text instead of a show-more toggle", () => {
        const workflow = iwcWorkflow({ description: "Runs <b>Velocyto</b>   on 10X data" });
        const description = mountWorkflowCard(workflow).find(".curated-description");

        expect(description.text()).toBe("Runs Velocyto on 10X data");
        expect(description.attributes("title")).toBe("Runs Velocyto on 10X data");
    });

    it("decodes the entities a sanitized local annotation carries", () => {
        const description = mountWorkflowCard(
            localWorkflow({ description: "R&amp;D notes for &lt;10X&gt; runs" }),
        ).find(".curated-description");

        expect(description.text()).toBe("R&D notes for <10X> runs");
    });

    it("enables import for a registered user", () => {
        // Without this the handler tests below would still pass if the action
        // were disabled and therefore unclickable.
        const importAction = importActionOf(mountCard(stories.CatalogWorkflow));

        expect(importAction.disabled).toBe(false);
    });

    it("imports a catalog row through TRS with the values the server supplied", async () => {
        const wrapper = mountCard(stories.CatalogWorkflow);

        await clickImport(wrapper, CATALOG_WORKFLOW);

        expect(importTrsToolFromUrl).toHaveBeenCalledTimes(1);
        expect(importTrsToolFromUrl).toHaveBeenCalledWith(PINNED_TRS_URL);
        expect(copyWorkflow).not.toHaveBeenCalled();
        // Without this the test passes even when the import throws and is swallowed.
        expect(routerPush).toHaveBeenCalledWith("/workflows/list");
        expect(toastError).not.toHaveBeenCalled();
    });

    it("does not navigate when the import finishes after the user has left the page", async () => {
        let finishImport: (value: unknown) => void = () => {};
        importTrsToolFromUrl.mockReturnValue(new Promise((resolve) => (finishImport = resolve)));
        const toastSuccess = vi.spyOn(Toast, "success").mockImplementation(() => {});
        toastSuccess.mockClear();
        const wrapper = mountCard(stories.CatalogWorkflow);

        await clickImport(wrapper, CATALOG_WORKFLOW);
        wrapper.unmount();
        finishImport({ id: "abc123", message: "Imported", status: "ok" });
        await flushPromises();

        expect(routerPush).not.toHaveBeenCalled();
        // Still told it worked, just without being pulled off the page they moved to.
        expect(toastSuccess).toHaveBeenCalledTimes(1);
    });

    it("surfaces a failed TRS import instead of navigating", async () => {
        const wrapper = mountCard(stories.DockstoreUnreachable);

        await clickImport(wrapper, workflowOf(stories.DockstoreUnreachable));

        // Only a missing release falls back; any other failure is reported as is.
        expect(importTrsToolFromUrl).toHaveBeenCalledTimes(1);
        expect(routerPush).not.toHaveBeenCalled();
        // The story play reads the visible failure message.
        expect(toastError).toHaveBeenCalledTimes(1);
    });

    it("falls back to the branch when the release is not on the TRS server yet", async () => {
        const wrapper = mountCard(stories.ReleaseNotOnDockstoreYet);

        await clickImport(wrapper, workflowOf(stories.ReleaseNotOnDockstoreYet));

        expect(importTrsToolFromUrl.mock.calls).toEqual([[PINNED_TRS_URL], [BRANCH_TRS_URL]]);
        expect(routerPush).toHaveBeenCalledWith("/workflows/list");
        expect(toastError).not.toHaveBeenCalled();
    });

    it("reports a missing release when there is no branch to fall back to", async () => {
        const wrapper = mountCard(stories.NotOnDockstore);

        await clickImport(wrapper, workflowOf(stories.NotOnDockstore));

        expect(importTrsToolFromUrl).toHaveBeenCalledTimes(1);
        expect(routerPush).not.toHaveBeenCalled();
        // The story play reads the visible failure message.
        expect(toastError).toHaveBeenCalledTimes(1);
    });

    it("asks to filter by a collection when its badge is clicked", async () => {
        const wrapper = mountCard(stories.CatalogWorkflow);

        const badge = wrapper.get("[id^='g-card-badge-curated-collection-']");
        expect(badge.text()).toContain("Single Cell");
        await badge.trigger("click");

        expect(wrapper.getComponent(CuratedWorkflowCard).emitted("collectionClick")).toEqual([["Single Cell"]]);
    });

    it("says a workflow is ready to run when nothing is missing", () => {
        const wrapper = mountCard(stories.CatalogWorkflow);

        expect(badgeById(wrapper, "curated-runnable")).toMatchObject({ label: "Ready to run", variant: "success" });
    });

    it("counts the missing tools in the footer and names them by their short id", () => {
        const workflow = iwcWorkflow({
            missing_tools: [
                "toolshed.g2.bx.psu.edu/repos/iuc/fastp/fastp/0.23.4+galaxy0",
                "toolshed.g2.bx.psu.edu/repos/iuc/multiqc/multiqc/1.11+galaxy1",
                "wig_to_bigWig",
            ],
        });
        const wrapper = mountWorkflowCard(workflow);
        const missing = missingToolsOf(wrapper, workflow);

        expect(missing.text()).toBe("Needs 3 tools");
        expect(missing.attributes("title")).toBe("Not installed on this Galaxy: fastp, multiqc, wig_to_bigWig");
        // Missing tools are the norm on most instances, so they stay out of the colored title-row badges.
        expect(wrapper.findComponent(GCard).props("badges")).toEqual([]);
    });

    describe("a catalog workflow the user has already imported", () => {
        function primaryIds(wrapper: ReturnType<typeof mountCard>) {
            return (wrapper.findComponent(GCard).props("primaryActions") ?? []).map(
                (action: { id: string }) => action.id,
            );
        }

        it("runs the user's copy instead of offering an import", () => {
            const workflow = iwcWorkflow({ imported_workflow_id: "abc123", imported_version: "v0.1" });
            const wrapper = mountWorkflowCard(workflow);
            const card = wrapper.findComponent(GCard);

            expect(primaryIds(wrapper)).toEqual(["curated-run"]);
            expect(nth(card.props("primaryActions"), 0).to).toBe("/workflows/run?id=abc123");
            // Importing the same TRS version again hands back this copy rather than making a new one.
            expect(actionIds(wrapper)).not.toContain("curated-import");
            expect(wrapper.find(`#g-card-badge-curated-imported-${workflow.id}`).text()).toBe("In your workflows");
        });

        it.each([
            ["the user's copy is older", "0.2", "v0.1"],
            ["the releases differ only numerically, not as text", "0.10", "v0.9"],
        ])("offers the newer release as another import when %s", (_, release, imported) => {
            const workflow = iwcWorkflow({ release, imported_workflow_id: "abc123", imported_version: imported });
            const wrapper = mountWorkflowCard(workflow);

            expect(primaryIds(wrapper)).toEqual(["curated-run", "curated-import"]);
            expect(importActionOf(wrapper).label).toBe(`Import v${release}`);
            expect(wrapper.find(`#g-card-badge-curated-update-available-${workflow.id}`).text()).toBe(
                `You have ${imported}`,
            );
        });

        it.each([
            ["a copy newer than the catalog's release", "0.2", "v0.3"],
            ["a copy of the same release", "0.10", "v0.10"],
            ["the same release written with a patch number", "0.1", "v0.1.0"],
        ])("offers no update for %s", (_, release, imported) => {
            const wrapper = mountWorkflowCard(
                iwcWorkflow({ release, imported_workflow_id: "abc123", imported_version: imported }),
            );

            expect(primaryIds(wrapper)).toEqual(["curated-run"]);
        });

        it("does not call a copy imported from the branch out of date", () => {
            const wrapper = mountWorkflowCard(
                iwcWorkflow({ release: "0.2", imported_workflow_id: "abc123", imported_version: "main" }),
            );

            expect(primaryIds(wrapper)).toEqual(["curated-run"]);
        });
    });

    describe("asking the admins for missing tools", () => {
        const MISSING = ["toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.7.17"];

        it("asks the list to request the tools, from the menu or the missing-tools note", async () => {
            const workflow = iwcWorkflow({ missing_tools: MISSING });
            const wrapper = await mountRequestCard(workflow);

            await missingToolsOf(wrapper, workflow).find("button").trigger("click");
            extraActionById(wrapper, "curated-request-tools").handler!();

            expect(wrapper.getComponent(CuratedWorkflowCard).emitted("requestTools")).toEqual([[workflow], [workflow]]);
        });

        it("stops offering the request once it has been sent", async () => {
            const workflow = iwcWorkflow({ missing_tools: MISSING });
            const wrapper = await mountRequestCard(workflow, false, { installationRequested: true });

            expect(extraActionById(wrapper, "curated-request-tools")).toMatchObject({
                label: "Installation requested",
                disabled: true,
            });
            expect(missingToolsOf(wrapper, workflow).find("button").exists()).toBe(false);
        });

        it("offers nothing when the workflow lacks no tools", async () => {
            expect(actionIds(await mountRequestCard(iwcWorkflow({ missing_tools: [] })))).not.toContain(
                "curated-request-tools",
            );
        });

        it("offers nothing when the request form is off", async () => {
            const workflow = iwcWorkflow({ missing_tools: MISSING });
            const wrapper = await mountRequestCard(workflow, false, {}, false);

            expect(actionIds(wrapper)).not.toContain("curated-request-tools");
            expect(missingToolsOf(wrapper, workflow).find("button").exists()).toBe(false);
        });

        it("offers nothing to anonymous users", async () => {
            const wrapper = await mountRequestCard(iwcWorkflow({ missing_tools: MISSING }), true);

            expect(actionIds(wrapper)).not.toContain("curated-request-tools");
        });
    });

    it("copies a locally hosted workflow instead of importing it through TRS", async () => {
        const wrapper = mountCard(stories.HostedHere);

        await clickImport(wrapper, workflowOf(stories.HostedHere));

        expect(copyWorkflow).toHaveBeenCalledWith("f2db41e1fa331b3e", "curator");
        expect(importTrsToolFromUrl).not.toHaveBeenCalled();
        expect(toastError).not.toHaveBeenCalled();
    });

    it.each([
        ["catalog", stories.CatalogWorkflow, importTrsToolFromUrl],
        ["local", stories.HostedHere, vi.mocked(copyWorkflow)],
    ])("ignores repeat clicks while a %s import is in flight", async (_kind, story, importCall) => {
        const pending = deferred<unknown>();
        importCall.mockReturnValue(pending.promise as never);
        const wrapper = mountCard(story);
        onTestFinished(async () => {
            pending.resolve({ id: "abc123", message: "Imported", status: "success" });
            await flushPromises();
        });
        const importAction = () => importActionOf(wrapper);

        const first = importAction().handler();
        await wrapper.vm.$nextTick();
        expect(importAction().disabled).toBe(true);
        await importAction().handler();
        expect(importCall).toHaveBeenCalledTimes(1);

        pending.resolve({ id: "abc123", message: "Imported", status: "success" });
        await first;
        await flushPromises();
        expect(importAction().disabled).toBe(false);
    });
});
