import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, suppressBootstrapVueWarnings } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import VueRouter from "vue-router";

import { useServerMock } from "@/api/client/__mocks__";
import type { CuratedWorkflow, CuratedWorkflowsIndexResponse } from "@/api/curatedWorkflows";
import { useUserStore } from "@/stores/userStore";

import CuratedWorkflowList from "./CuratedWorkflowList.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";

const { server, http } = useServerMock();

const localVue = getLocalVue();
localVue.use(VueRouter);
const router = new VueRouter();

const FAKE_USER = getFakeRegisteredUser();

/** Query parameters of every catalog request, in order. */
let catalogQueries: URLSearchParams[] = [];

/** What the mocked /api/configuration reports as curated_workflows_source. */
let configSource = "iwc";

/** Records any hit on the badge counts endpoint, which curated cards must never make. */
const countsRequested = vi.fn();

function iwcWorkflow(overrides: Partial<CuratedWorkflow> = {}): CuratedWorkflow {
    return {
        id: "iwc-workflow-1",
        name: "Velocyto on 10x filtered barcodes",
        description: "A curated single cell workflow",
        tags: ["single-cell"],
        collections: ["single-cell"],
        number_of_steps: 5,
        update_time: "2026-01-01T00:00:00",
        release: "0.1",
        doi: "10.5281/zenodo.1234567",
        external_url: "https://iwc.galaxyproject.org/workflow/iwc-workflow-1/",
        owner: null,
        stored_workflow_id: null,
        trs_url:
            "https://dockstore.org/api/ga4gh/trs/v2/tools/%23workflow%2Fgithub.com%2Fiwc-workflows%2Fvelocyto%2Fmain/versions/v0.1",
        trs_fallback_url:
            "https://dockstore.org/api/ga4gh/trs/v2/tools/%23workflow%2Fgithub.com%2Fiwc-workflows%2Fvelocyto%2Fmain/versions/main",
        ...overrides,
    };
}

function localWorkflow(overrides: Partial<CuratedWorkflow> = {}): CuratedWorkflow {
    return {
        id: "f2db41e1fa331b3e",
        name: "Locally curated workflow",
        description: "Published on this Galaxy",
        tags: ["curated"],
        collections: [],
        number_of_steps: 3,
        update_time: "2026-01-02T00:00:00",
        release: null,
        doi: null,
        external_url: null,
        owner: "curator",
        stored_workflow_id: "f2db41e1fa331b3e",
        trs_url: null,
        trs_fallback_url: null,
        ...overrides,
    };
}

type CatalogResponder = (
    query: URLSearchParams,
) => CuratedWorkflowsIndexResponse | Promise<CuratedWorkflowsIndexResponse>;

function useCatalog(respondWith: CatalogResponder) {
    server.use(
        http.get("/api/workflows/curated", async ({ request, response: respond }) => {
            const query = new URL(request.url).searchParams;
            catalogQueries.push(query);
            return respond(200).json(await respondWith(query));
        }),
    );
}

async function mountList() {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);

    const userStore = useUserStore();
    userStore.currentUser = FAKE_USER;

    const wrapper = mount(CuratedWorkflowList as object, {
        localVue,
        pinia,
        router,
    });

    await flushPromises();

    return wrapper;
}

async function mountCuratedList(response: CuratedWorkflowsIndexResponse) {
    useCatalog(() => response);
    return mountList();
}

async function setFilterText(wrapper: Awaited<ReturnType<typeof mountList>>, text: string) {
    wrapper.findComponent(FilterMenu).vm.$emit("update:filterText", text);
    await flushPromises();
}

function deferred<T>() {
    let resolve: (value: T) => void = () => {};
    const promise = new Promise<T>((res) => (resolve = res));
    return { promise, resolve };
}

function iwcPage(ids: string[], totalMatches = ids.length): CuratedWorkflowsIndexResponse {
    return {
        source: "iwc",
        total_matches: totalMatches,
        workflows: ids.map((id) => iwcWorkflow({ id, name: `Workflow ${id}` })),
    };
}

describe("CuratedWorkflowList", () => {
    beforeEach(() => {
        suppressBootstrapVueWarnings();
        vi.clearAllMocks();
        catalogQueries = [];
        configSource = "iwc";
        server.use(
            // WorkflowListTabs and the sort header read the config store, which
            // fetches eagerly when it is first instantiated.
            http.get("/api/configuration", ({ response }) => {
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                return response(200).json({ curated_workflows_source: configSource } as any);
            }),
            http.get("/api/workflows/{workflow_id}/counts", ({ response }) => {
                countsRequested();
                return response(200).json({});
            }),
        );
    });

    it("renders a card per workflow for the iwc source", async () => {
        const workflows = [
            iwcWorkflow(),
            iwcWorkflow({ id: "iwc-workflow-2", name: "Another curated workflow" }),
            iwcWorkflow({ id: "iwc-workflow-3", name: "A third curated workflow" }),
        ];
        const wrapper = await mountCuratedList({ source: "iwc", total_matches: 3, workflows });

        expect(wrapper.findAll(".curated-workflow-card")).toHaveLength(3);
        expect(wrapper.find("#curated-workflows-source-note").exists()).toBe(true);
        expect(wrapper.find("#curated-workflows-preparing").exists()).toBe(false);
        expect(wrapper.find("#curated-workflows-unavailable").exists()).toBe(false);
        expect(wrapper.find("#curated-workflows-empty").exists()).toBe(false);
    });

    it("offers import but not run for iwc rows, and never requests workflow counts", async () => {
        const workflow = iwcWorkflow();
        const wrapper = await mountCuratedList({ source: "iwc", total_matches: 1, workflows: [workflow] });

        expect(wrapper.find(`#g-card-action-curated-import-${workflow.id}`).exists()).toBe(true);
        expect(wrapper.find(`#g-card-action-curated-run-${workflow.id}`).exists()).toBe(false);

        // The curated card deliberately avoids the workflow card badge composables,
        // whose keyed cache getter fires this request as a side effect.
        expect(countsRequested).not.toHaveBeenCalled();
    });

    it("renders a card per workflow for the local source", async () => {
        const workflows = [localWorkflow(), localWorkflow({ id: "abc123", stored_workflow_id: "abc123" })];
        const wrapper = await mountCuratedList({ source: "local", total_matches: 2, workflows });

        expect(wrapper.findAll(".curated-workflow-card")).toHaveLength(2);
        expect(wrapper.find("#g-card-action-curated-run-f2db41e1fa331b3e").exists()).toBe(true);
        expect(countsRequested).not.toHaveBeenCalled();
    });

    it("sends valid filter text to the server as the search", async () => {
        const wrapper = await mountCuratedList(iwcPage(["a"]));

        await setFilterText(wrapper, "name:foo");

        expect(catalogQueries).toHaveLength(2);
        expect(catalogQueries[1]!.get("search")).toBe("name:foo");
    });

    it("reports an invalid filter without sending it to the server", async () => {
        const wrapper = await mountCuratedList(iwcPage(["a"]));

        await setFilterText(wrapper, "owner:bob");

        expect(wrapper.find("#no-curated-workflow-found-invalid").exists()).toBe(true);
        expect(wrapper.find("#no-curated-workflow-found-invalid").text()).toContain("owner");
        expect(catalogQueries).toHaveLength(1);
    });

    it("renders the latest request's rows even when an older response lands after it", async () => {
        const first = deferred<CuratedWorkflowsIndexResponse>();
        const second = deferred<CuratedWorkflowsIndexResponse>();
        const pending = [first, second];
        useCatalog(() => pending.shift()!.promise);
        const wrapper = await mountList();

        await setFilterText(wrapper, "name:second");
        expect(catalogQueries).toHaveLength(2);

        second.resolve(iwcPage(["second"]));
        await flushPromises();
        first.resolve(iwcPage(["first"]));
        await flushPromises();

        const cards = wrapper.findAll(".curated-workflow-card");
        expect(cards).toHaveLength(1);
        expect(cards.at(0).text()).toContain("Workflow second");
    });

    it("steps back to the last page that exists when the catalog shrinks underneath the user", async () => {
        const fullPage = Array.from({ length: 24 }, (_, index) => `wf-${index}`);
        useCatalog((query) => {
            const offset = Number(query.get("offset"));
            if (offset === 0) {
                return iwcPage(fullPage, 60);
            }
            // The catalog has shrunk to 30 by the time page 3 is asked for.
            return offset === 48 ? iwcPage([], 30) : iwcPage(fullPage.slice(0, 6), 30);
        });
        const wrapper = await mountList();

        wrapper.findComponent({ name: "BPagination" }).vm.$emit("change", 3);
        await flushPromises();

        expect(catalogQueries.map((query) => query.get("offset"))).toEqual(["0", "48", "24"]);
        expect(wrapper.findAll(".curated-workflow-card")).toHaveLength(6);
    });

    it("keeps a failed request on screen as an error", async () => {
        server.use(
            http.get("/api/workflows/curated", ({ response }) => {
                return response("4XX").json(
                    { err_msg: "The curated workflows catalog is not enabled", err_code: 403004 },
                    { status: 403 },
                );
            }),
        );
        const wrapper = await mountList();

        expect(wrapper.find("#curated-workflows-error").exists()).toBe(true);
        expect(wrapper.find("#curated-workflows-error").text()).toContain("not enabled");
        expect(wrapper.findAll(".curated-workflow-card")).toHaveLength(0);
    });

    it("renders the preparing alert and no cards while the catalog is being fetched", async () => {
        const wrapper = await mountCuratedList({
            source: "preparing",
            total_matches: 0,
            workflows: [],
            message: "Galaxy is fetching the curated workflow catalog.",
        });

        expect(wrapper.find("#curated-workflows-preparing").exists()).toBe(true);
        expect(wrapper.find("#curated-workflows-preparing").text()).toContain("fetching the curated workflow catalog");
        expect(wrapper.findAll(".curated-workflow-card")).toHaveLength(0);
        expect(wrapper.find("#curated-workflows-unavailable").exists()).toBe(false);
    });

    it("renders the unavailable alert and no cards when the catalog cannot be reached", async () => {
        const wrapper = await mountCuratedList({
            source: "unavailable",
            total_matches: 0,
            workflows: [],
            message: "Galaxy could not reach the curated workflow catalog.",
        });

        expect(wrapper.find("#curated-workflows-unavailable").exists()).toBe(true);
        expect(wrapper.find("#curated-workflows-unavailable").text()).toContain("could not reach");
        expect(wrapper.findAll(".curated-workflow-card")).toHaveLength(0);
        expect(wrapper.find("#curated-workflows-preparing").exists()).toBe(false);
    });

    it("renders the empty alert for an unfiltered local catalog with no workflows", async () => {
        const wrapper = await mountCuratedList({ source: "local", total_matches: 0, workflows: [] });

        expect(wrapper.find("#curated-workflows-empty").exists()).toBe(true);
        expect(wrapper.find("#no-curated-workflow-found").exists()).toBe(false);
        expect(wrapper.findAll(".curated-workflow-card")).toHaveLength(0);
    });

    it("starts on Recommended and leaves the order to the server until the user picks a sort", async () => {
        const wrapper = await mountCuratedList({ source: "iwc", total_matches: 1, workflows: [iwcWorkflow()] });

        expect(wrapper.find("#sortby-default").classes()).toContain("g-pressed");
        expect(wrapper.find("#sortby-update_time").classes()).not.toContain("g-pressed");
        // Sending a sort at all would opt out of runnable-first ordering.
        expect(catalogQueries).toHaveLength(1);
        expect(catalogQueries[0]!.has("sort_by")).toBe(false);
        expect(catalogQueries[0]!.has("sort_desc")).toBe(false);

        await wrapper.find("#sortby-name").trigger("click");
        await flushPromises();

        expect(catalogQueries).toHaveLength(2);
        expect(catalogQueries[1]!.get("sort_by")).toBe("name");
        expect(catalogQueries[1]!.get("sort_desc")).toBe("true");
        expect(wrapper.find("#sortby-default").classes()).not.toContain("g-pressed");

        await wrapper.find("#sortby-default").trigger("click");
        await flushPromises();

        expect(catalogQueries).toHaveLength(3);
        expect(catalogQueries[2]!.has("sort_by")).toBe(false);
        expect(catalogQueries[2]!.has("sort_desc")).toBe(false);
        expect(wrapper.find("#sortby-default").classes()).toContain("g-pressed");
    });

    it("offers no Recommended sort in local mode, where the server default is newest first", async () => {
        configSource = "local";
        const wrapper = await mountCuratedList({ source: "local", total_matches: 1, workflows: [localWorkflow()] });

        expect(wrapper.find("#sortby-default").exists()).toBe(false);
        expect(wrapper.find("#sortby-update_time").classes()).toContain("g-pressed");
        expect(catalogQueries[0]!.has("sort_by")).toBe(false);

        // Already newest first, so the first click on it flips to oldest first.
        await wrapper.find("#sortby-update_time").trigger("click");
        await flushPromises();

        expect(catalogQueries[1]!.get("sort_by")).toBe("update_time");
        expect(catalogQueries[1]!.get("sort_desc")).toBe("false");
    });
});
