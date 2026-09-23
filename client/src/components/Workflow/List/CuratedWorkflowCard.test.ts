import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, suppressBootstrapVueWarnings } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import VueRouter from "vue-router";

import type { AnonymousUser } from "@/api";
import type { CuratedWorkflow } from "@/api/curatedWorkflows";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";
import { ApiError } from "@/utils/simple-error";

import CuratedWorkflowCard from "./CuratedWorkflowCard.vue";
import GCard from "@/components/Common/GCard.vue";

const importTrsToolFromUrl = vi.fn();
const copyWorkflow = vi.fn();

vi.mock("@/components/Workflow/services", () => ({
    Services: class MockServices {
        importTrsToolFromUrl(...args: unknown[]) {
            return importTrsToolFromUrl(...args);
        }
    },
}));

vi.mock("@/components/Workflow/workflows.services", () => ({
    copyWorkflow: (...args: unknown[]) => copyWorkflow(...args),
}));

vi.mock("@/components/Workflow/redirectPath", () => ({
    getRedirectOnImportPath: () => "/workflows/list",
}));

let toastError: ReturnType<typeof vi.spyOn>;
let routerPush: ReturnType<typeof vi.spyOn>;

const localVue = getLocalVue();
localVue.use(VueRouter);
const router = new VueRouter();

const VELOCYTO_TRS =
    "https://dockstore.org/api/ga4gh/trs/v2/tools/%23workflow%2Fgithub.com%2Fiwc-workflows%2Fvelocyto%2Fmain/versions";
const PINNED_TRS_URL = `${VELOCYTO_TRS}/v0.1`;
const BRANCH_TRS_URL = `${VELOCYTO_TRS}/main`;

const FAKE_USER = getFakeRegisteredUser();
const ANONYMOUS_USER = {
    isAnonymous: true,
    total_disk_usage: 0,
    nice_total_disk_usage: "0 bytes",
} as AnonymousUser;

function iwcWorkflow(overrides: Partial<CuratedWorkflow> = {}): CuratedWorkflow {
    return {
        id: "velocyto-velocyto-on10x-filtered-barcodes",
        name: "Velocyto on 10x filtered barcodes",
        description: "A curated single cell workflow",
        tags: ["single-cell"],
        collections: ["Single Cell"],
        number_of_steps: 5,
        update_time: "2026-01-01T00:00:00",
        release: "0.1",
        doi: "10.5281/zenodo.1234567",
        external_url: "https://iwc.galaxyproject.org/workflow/velocyto/",
        owner: null,
        stored_workflow_id: null,
        trs_url: PINNED_TRS_URL,
        trs_fallback_url: BRANCH_TRS_URL,
        missing_tools: [],
        ...overrides,
    };
}

function localWorkflow(overrides: Partial<CuratedWorkflow> = {}): CuratedWorkflow {
    return iwcWorkflow({
        id: "f2db41e1fa331b3e",
        name: "Locally curated workflow",
        stored_workflow_id: "f2db41e1fa331b3e",
        owner: "curator",
        external_url: null,
        doi: null,
        release: null,
        trs_url: null,
        trs_fallback_url: null,
        missing_tools: null,
        ...overrides,
    });
}

function mountCard(workflow: CuratedWorkflow, isAnonymous = false) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);

    const userStore = useUserStore();
    // An anonymous user is a non-null object without an email, not a null user.
    userStore.currentUser = isAnonymous ? ANONYMOUS_USER : { ...FAKE_USER };

    const wrapper = mount(CuratedWorkflowCard as object, {
        propsData: { workflow },
        localVue,
        router,
        pinia,
    });
    return wrapper;
}

function importActionOf(wrapper: ReturnType<typeof mountCard>) {
    return wrapper
        .findComponent(GCard)
        .props("primaryActions")
        .find((action: { id: string }) => action.id === "curated-import");
}

async function clickImport(wrapper: ReturnType<typeof mountCard>, workflow: CuratedWorkflow) {
    await wrapper.find(`#g-card-action-curated-import-${workflow.id}`).trigger("click");
    await flushPromises();
}

function badgeById(wrapper: ReturnType<typeof mountCard>, id: string) {
    const badges = wrapper.findComponent(GCard).props("badges") ?? [];
    return badges.find((badge: { id: string }) => badge.id === id);
}

function actionIds(wrapper: ReturnType<typeof mountCard>): string[] {
    const card = wrapper.findComponent(GCard);
    const actions = [...(card.props("primaryActions") ?? []), ...(card.props("extraActions") ?? [])];
    return actions.map((action: { id: string }) => action.id);
}

describe("CuratedWorkflowCard", () => {
    beforeEach(() => {
        suppressBootstrapVueWarnings();
        importTrsToolFromUrl.mockReset();
        copyWorkflow.mockReset();
        // Stubbed so the assertions can see navigation; a real push would also
        // warn about redundant routes across repeated mounts.
        routerPush = vi.spyOn(router, "push").mockResolvedValue(undefined as never);
        toastError = vi.spyOn(Toast, "error").mockImplementation(() => {});
        // spyOn hands back the existing spy, so calls would otherwise leak between tests.
        toastError.mockClear();
    });

    afterEach(() => {
        routerPush.mockRestore();
    });

    it("renders the title as plain text with no preview link", () => {
        // A catalog row's id is an IWC slug, so a preview modal keyed on it would 404.
        const workflow = iwcWorkflow();
        const wrapper = mountCard(workflow);
        const title = wrapper.find(`#g-card-title-${workflow.id}`);

        expect(title.text()).toContain("Velocyto on 10x filtered barcodes");
        expect(wrapper.find(`#g-card-title-link-${workflow.id}`).exists()).toBe(false);
        expect(title.find("a").exists()).toBe(false);
    });

    it("marks the card so Selenium's workflow-card count is unaffected", () => {
        const wrapper = mountCard(iwcWorkflow());

        expect(wrapper.classes()).toContain("curated-workflow-card");
        expect(wrapper.classes()).not.toContain("workflow-card");
    });

    it("offers import and external links for a catalog row", () => {
        const ids = actionIds(mountCard(iwcWorkflow()));

        expect(ids).toContain("curated-import");
        expect(ids).toContain("curated-external-link");
        expect(ids).toContain("curated-doi");
        expect(ids).not.toContain("curated-run");
    });

    it("offers run and view for a workflow hosted on this Galaxy", () => {
        const ids = actionIds(mountCard(localWorkflow()));

        expect(ids).toContain("curated-run");
        expect(ids).toContain("curated-import");
        expect(ids).toContain("curated-open");
        expect(ids).not.toContain("curated-external-link");
    });

    it("enables import for a registered user", () => {
        // Without this the handler tests below would still pass if the action
        // were disabled and therefore unclickable.
        const importAction = importActionOf(mountCard(iwcWorkflow()));

        expect(importAction.disabled).toBe(false);
    });

    it("disables import for a catalog row with no TRS URL to import", () => {
        const importAction = importActionOf(mountCard(iwcWorkflow({ trs_url: null })));

        expect(importAction.disabled).toBe(true);
    });

    it("disables import for anonymous users", () => {
        const importAction = importActionOf(mountCard(iwcWorkflow(), true));

        expect(importAction.disabled).toBe(true);
        expect(importAction.title).toBe("Log in to import this workflow");
    });

    it("imports a catalog row through TRS with the values the server supplied", async () => {
        importTrsToolFromUrl.mockResolvedValue({ id: "abc123", message: "Imported", status: "ok" });
        const workflow = iwcWorkflow();
        const wrapper = mountCard(workflow);

        await clickImport(wrapper, workflow);

        expect(importTrsToolFromUrl).toHaveBeenCalledTimes(1);
        expect(importTrsToolFromUrl).toHaveBeenCalledWith(PINNED_TRS_URL);
        expect(copyWorkflow).not.toHaveBeenCalled();
        // Without this the test passes even when the import throws and is swallowed.
        expect(routerPush).toHaveBeenCalledWith("/workflows/list");
        expect(toastError).not.toHaveBeenCalled();
    });

    it("surfaces a failed TRS import instead of navigating", async () => {
        importTrsToolFromUrl.mockRejectedValue(new ApiError("dockstore is down", 502));
        const workflow = iwcWorkflow();
        const wrapper = mountCard(workflow);

        await clickImport(wrapper, workflow);

        // Only a missing release falls back; any other failure is reported as is.
        expect(importTrsToolFromUrl).toHaveBeenCalledTimes(1);
        expect(routerPush).not.toHaveBeenCalled();
        expect(toastError).toHaveBeenCalled();
    });

    it("falls back to the branch when the release is not on the TRS server yet", async () => {
        importTrsToolFromUrl
            .mockRejectedValueOnce(new ApiError("version not found", 404))
            .mockResolvedValueOnce({ id: "abc123", message: "Imported", status: "ok" });
        const workflow = iwcWorkflow();
        const wrapper = mountCard(workflow);

        await clickImport(wrapper, workflow);

        expect(importTrsToolFromUrl.mock.calls).toEqual([[PINNED_TRS_URL], [BRANCH_TRS_URL]]);
        expect(routerPush).toHaveBeenCalledWith("/workflows/list");
        expect(toastError).not.toHaveBeenCalled();
    });

    it("reports a missing release when there is no branch to fall back to", async () => {
        importTrsToolFromUrl.mockRejectedValue(new ApiError("version not found", 404));
        const workflow = iwcWorkflow({ trs_fallback_url: null });
        const wrapper = mountCard(workflow);

        await clickImport(wrapper, workflow);

        expect(importTrsToolFromUrl).toHaveBeenCalledTimes(1);
        expect(routerPush).not.toHaveBeenCalled();
        expect(toastError).toHaveBeenCalled();
    });

    it("says a workflow is ready to run when nothing is missing", () => {
        const wrapper = mountCard(iwcWorkflow({ missing_tools: [] }));

        expect(badgeById(wrapper, "curated-runnable")).toMatchObject({ label: "Ready to run", variant: "success" });
        expect(badgeById(wrapper, "curated-missing-tools")).toBeUndefined();
    });

    it("counts the missing tools and names them by their short id", () => {
        const wrapper = mountCard(
            iwcWorkflow({
                missing_tools: [
                    "toolshed.g2.bx.psu.edu/repos/iuc/fastp/fastp/0.23.4+galaxy0",
                    "toolshed.g2.bx.psu.edu/repos/iuc/multiqc/multiqc/1.11+galaxy1",
                    "wig_to_bigWig",
                ],
            }),
        );
        const badge = badgeById(wrapper, "curated-missing-tools");

        expect(badge).toMatchObject({ label: "Needs 3 tools", variant: "warning" });
        expect(badge.title).toBe("Not installed on this Galaxy: fastp, multiqc, wig_to_bigWig");
        expect(badgeById(wrapper, "curated-runnable")).toBeUndefined();
    });

    it("keeps import enabled when tools are missing, so an admin can import and install them", () => {
        const wrapper = mountCard(iwcWorkflow({ missing_tools: ["wig_to_bigWig"] }));

        expect(badgeById(wrapper, "curated-missing-tools").label).toBe("Needs 1 tool");
        expect(importActionOf(wrapper).disabled).toBe(false);
    });

    it("shows no runnability badge when the server did not check", () => {
        const wrapper = mountCard(localWorkflow());

        expect(badgeById(wrapper, "curated-runnable")).toBeUndefined();
        expect(badgeById(wrapper, "curated-missing-tools")).toBeUndefined();
    });

    it("copies a locally hosted workflow instead of importing it through TRS", async () => {
        const workflow = localWorkflow();
        const wrapper = mountCard(workflow);

        await clickImport(wrapper, workflow);

        expect(copyWorkflow).toHaveBeenCalledWith("f2db41e1fa331b3e", "curator");
        expect(importTrsToolFromUrl).not.toHaveBeenCalled();
    });

    it.each([
        ["catalog", iwcWorkflow, importTrsToolFromUrl],
        ["local", localWorkflow, copyWorkflow],
    ])("ignores repeat clicks while a %s import is in flight", async (_kind, makeWorkflow, importCall) => {
        let finishImport: (value: unknown) => void = () => {};
        importCall.mockReturnValue(new Promise((resolve) => (finishImport = resolve)));
        const wrapper = mountCard(makeWorkflow());
        const importAction = () => importActionOf(wrapper);

        const first = importAction().handler();
        await wrapper.vm.$nextTick();
        expect(importAction().disabled).toBe(true);
        await importAction().handler();
        expect(importCall).toHaveBeenCalledTimes(1);

        finishImport({ id: "abc123", message: "Imported", status: "ok" });
        await first;
        await flushPromises();
        expect(importAction().disabled).toBe(false);
    });
});
