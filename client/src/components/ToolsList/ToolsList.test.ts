import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import toolsListUntyped from "@/components/ToolsView/testData/toolsList.json";
import type { Tool } from "@/stores/toolStore";
import { useToolStore } from "@/stores/toolStore";

import ToolFilterChip from "./ToolFilterChip.vue";
import ToolsList from "./ToolsList.vue";
import ToolsListSectionFilters from "./ToolsListSectionFilters.vue";
import ToolsListTable from "./ToolsListTable.vue";
import ToolsListTagFilter from "./ToolsListTagFilter.vue";

const FILTER_INPUTS = {
    "[placeholder='any name']": "name-filter",
    "[placeholder='any EDAM ontology']": "ontology-filter",
    "[placeholder='any id']": "id-filter",
    "[placeholder='any repository owner']": "owner-filter",
    "[placeholder='any help text']": "help-filter",
};
const FILTER_SETTINGS = {
    name: "name-filter",
    ontology: "ontology-filter",
    id: "id-filter",
    owner: "owner-filter",
    help: "help-filter",
};
// Expected Whoosh queries are hard-coded so a regression in `createWhooshQuery`
// can't make both sides of the assertion wrong simultaneously. The canonical
// `createWhooshQuery` test lives in `../Panels/utilities.test.ts`.
const WHOOSH_QUERY =
    "(name:(name-filter) name_exact:(name-filter) description:(name-filter))" +
    " AND (ontology:(ontology-filter) AND id_exact:(id-filter) AND owner:(owner-filter) AND help:(help-filter))";
const TAG_FILTER_SETTINGS = {
    tag: ["collection_ops", "data cleanup"],
};
const TAG_WHOOSH_QUERY = '(tool_tags:(collection_ops) AND tool_tags:("data cleanup"))';
const RAW_TAG_SEARCH = 'tag:"data cleanup" OR tag:collection_ops';
const RAW_TAG_WHOOSH_QUERY = 'tool_tags:("data cleanup") OR tool_tags:(collection_ops)';
const MIXED_TAG_SEARCH = 'tag:"data cleanup" trim';
const MIXED_TAG_WHOOSH_QUERY = '(trim) AND (tool_tags:("data cleanup"))';
const MIXED_TAG_AND_ONTOLOGY_SEARCH = 'tag:"Join, Subtract and Group" ontology:"operation_3695"';
const MIXED_TAG_AND_ONTOLOGY_FILTER_SETTINGS = {
    tag: ["Join, Subtract and Group"],
    ontology: '"operation_3695"',
};
const MIXED_TAG_AND_ONTOLOGY_WHOOSH_QUERY =
    '(tool_tags:("join, subtract and group") AND edam_operations:("operation_3695"))';
const toolsList = toolsListUntyped as unknown as Tool[];

const routerPushMock = vi.fn();

// The component reads the router via `useRouter()` (mocked here) while child
// components (e.g. GButton's `<RouterLink>`) need a real router on the mount
// option to render -- getLocalVue() provides that default router now, so we
// only need to override useRouter() itself.
vi.mock("vue-router", async (importOriginal) => {
    const actual = (await importOriginal()) as Record<string, unknown>;
    return {
        ...actual,
        useRouter: () => ({
            push: routerPushMock,
        }),
    };
});

const localVue = getLocalVue();
const router = injectTestRouter(localVue);

describe("ToolsList", () => {
    let fetchToolsMock: ReturnType<typeof vi.spyOn>;
    let pinia: ReturnType<typeof createTestingPinia>;

    beforeEach(() => {
        pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        setActivePinia(pinia);

        const toolStore = useToolStore(pinia);
        toolStore.saveAllTools(toolsList);
        fetchToolsMock = vi.spyOn(toolStore, "fetchTools").mockResolvedValue();
        vi.spyOn(toolStore, "fetchToolSections").mockResolvedValue();
        vi.spyOn(toolStore, "fetchToolTagsMapping").mockResolvedValue();
        vi.spyOn(toolStore, "fetchHelpForId").mockResolvedValue();

        // Clear the router mock between tests
        routerPushMock.mockClear();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it.each(["#favorites", "fastqc #favs", RAW_TAG_SEARCH, "tag:alpha OR tag:beta"])(
        "keeps unrepresentable search %s out of the structured pickers",
        async (search) => {
            const wrapper = mount(ToolsList as object, { localVue, pinia, router, propsData: { search } });
            await flushPromises();
            expect(wrapper.findComponent(ToolsListTagFilter).props("selectedTags")).toEqual([]);
            expect(wrapper.findComponent(ToolsListTagFilter).props("disabled")).toBe(true);
            expect(wrapper.get(".tool-tags-dropdown button.dropdown-toggle").attributes("disabled")).toBeDefined();
            expect(wrapper.get(".tool-section-dropdown button.dropdown-toggle").attributes("disabled")).toBeDefined();
            expect(wrapper.find('button[title^="Remove tag"]').exists()).toBe(false);
            expect(wrapper.text()).not.toContain("Tools must match all selected tags.");
            expect(wrapper.text()).toContain("Edit this search in the search field to preserve its conditions.");
            expect((wrapper.get("input.search-query").element as HTMLInputElement).value).toBe(search);
            await wrapper.get('[data-description="clear-all-tool-filters"]').trigger("click");
            await flushPromises();
            expect(wrapper.findComponent(ToolsListTagFilter).props("disabled")).toBe(false);
        },
    );

    it.each([
        ["fastqc", [], 'fastqc tag:"data cleanup"', '(fastqc) AND (tool_tags:("data cleanup"))'],
        [
            "owner:devteam fastqc",
            [],
            'fastqc owner:devteam tag:"data cleanup"',
            '(fastqc) AND ((owner:(devteam) AND tool_tags:("data cleanup")))',
        ],
        [
            "tag:collection_ops fastqc",
            ["collection_ops"],
            'fastqc tag:collection_ops tag:"data cleanup"',
            '(fastqc) AND ((tool_tags:(collection_ops) AND tool_tags:("data cleanup")))',
        ],
        [MIXED_TAG_SEARCH, ["data cleanup"], "trim", "trim"],
        ["unknown:term", [], 'unknown:term tag:"data cleanup"', '(unknown:term) AND (tool_tags:("data cleanup"))'],
    ])(
        "keeps the free text of %s when toggling a tag with the picker",
        async (search, selectedTags, expectedSearch, expectedQuery) => {
            const wrapper = mount(ToolsList as object, { localVue, pinia, router, propsData: { search } });
            await flushPromises();
            const selector = wrapper.findComponent(ToolsListTagFilter);
            expect(selector.props("disabled")).toBe(false);
            expect(selector.props("selectedTags")).toEqual(selectedTags);
            expect(wrapper.text()).not.toContain("Edit this search in the search field to preserve its conditions.");
            selector.vm.$emit("toggle-tag", "data cleanup");
            await flushPromises();
            expect((wrapper.get("input.search-query").element as HTMLInputElement).value).toBe(expectedSearch);
            expect(routerPushMock).toHaveBeenLastCalledWith({ path: "/tools/list", query: { search: expectedSearch } });
            expect(fetchToolsMock).toHaveBeenLastCalledWith(expectedQuery);
        },
    );

    it.each([
        ["fastqc name:foo name:bar", 'fastqc name:foo name:bar tag:"data cleanup"'],
        ['fastqc help:"format: SAM"', 'fastqc help:"format: SAM" tag:"data cleanup"'],
        ['fastqc tag:"Data Cleanup" owner:devteam', "fastqc owner:devteam"],
    ])("keeps every other condition of %s when toggling a tag with the picker", async (search, expectedSearch) => {
        const wrapper = mount(ToolsList as object, { localVue, pinia, router, propsData: { search } });
        await flushPromises();
        wrapper.findComponent(ToolsListTagFilter).vm.$emit("toggle-tag", "data cleanup");
        await flushPromises();
        expect((wrapper.get("input.search-query").element as HTMLInputElement).value).toBe(expectedSearch);
    });

    it("keeps the free text when choosing an ontology with the picker", async () => {
        const wrapper = mount(ToolsList as object, { localVue, pinia, router, propsData: { search: "fastqc" } });
        await flushPromises();
        expect(wrapper.get(".tool-section-dropdown button.dropdown-toggle").attributes("disabled")).toBeUndefined();
        wrapper.findComponent(ToolsListSectionFilters).vm.$emit("apply-filter", "ontology", '"operation_1"');
        await flushPromises();
        expect((wrapper.get("input.search-query").element as HTMLInputElement).value).toBe(
            'fastqc ontology:"operation_1"',
        );
        expect(fetchToolsMock).toHaveBeenLastCalledWith("(fastqc) AND (edam_operations:(operation_1))");
    });

    it("labels the reset button by what it clears", async () => {
        const wrapper = mount(ToolsList as object, { localVue, pinia, router, propsData: { search: "fastqc" } });
        await flushPromises();
        expect(wrapper.get('[data-description="clear-all-tool-filters"]').text()).toBe("Clear search");
        wrapper.findComponent(ToolsListTagFilter).vm.$emit("toggle-tag", "data cleanup");
        await flushPromises();
        expect(wrapper.get('[data-description="clear-all-tool-filters"]').text()).toBe("Clear all filters");
    });

    it("reports a failed tag catalog request in the tag picker", async () => {
        vi.spyOn(useToolStore(), "fetchToolTagsMapping").mockRejectedValue(new Error("boom"));
        const wrapper = mount(ToolsList as object, { localVue, pinia, router });
        await flushPromises();
        const selector = wrapper.findComponent(ToolsListTagFilter);
        expect(selector.props("loading")).toBe(false);
        await wrapper.get(".tool-tags-dropdown button.dropdown-toggle").trigger("click");
        expect(selector.text()).toContain("Could not load tags/categories.");
        expect(selector.text()).not.toContain("No tags available.");
    });

    it("only offers to favorite ontology filters that are EDAM terms", async () => {
        const wrapper = mount(ToolsList as object, { localVue, pinia, router, propsData: { ontology: "foo" } });
        await flushPromises();
        const chip = wrapper.findComponent(ToolFilterChip);
        expect(chip.find('button[title="Remove ontology foo"]').exists()).toBe(true);
        expect(chip.findAll("button")).toHaveLength(1);

        const edamWrapper = mount(ToolsList as object, {
            localVue,
            pinia,
            router,
            propsData: { ontology: '"topic_0003"' },
        });
        await flushPromises();
        expect(edamWrapper.findComponent(ToolFilterChip).findAll("button")).toHaveLength(2);
    });

    it("supports a structured tag with AND in its quoted name", async () => {
        const wrapper = mount(ToolsList as object, {
            localVue,
            pinia,
            router,
            propsData: { tag: ["DNA AND RNA"] },
        });
        await flushPromises();
        expect(wrapper.findComponent(ToolsListTagFilter).props("selectedTags")).toEqual(["DNA AND RNA"]);
        expect(wrapper.findComponent(ToolsListTagFilter).props("disabled")).toBe(false);
        expect(fetchToolsMock).toHaveBeenCalledWith('(tool_tags:("dna and rna"))');
    });

    it("explains tag matching and clears all filters, chips, and URL parameters", async () => {
        const wrapper = mount(ToolsList as object, {
            localVue,
            pinia,
            router,
            propsData: { tag: ["data cleanup", "collection_ops"], ontology: '"operation_1"', owner: "devteam" },
        });
        await flushPromises();
        expect(wrapper.text()).toContain("Tools must match all selected tags.");
        expect(wrapper.find('button[title="Remove ontology operation_1"]').exists()).toBe(true);
        await wrapper.get('[data-description="clear-all-tool-filters"]').trigger("click");
        await flushPromises();
        expect((wrapper.get("input.search-query").element as HTMLInputElement).value).toBe("");
        expect(wrapper.findComponent(ToolsListTagFilter).props("selectedTags")).toEqual([]);
        expect(wrapper.find('button[title="Remove ontology operation_1"]').exists()).toBe(false);
        expect(wrapper.find('[data-description="clear-all-tool-filters"]').exists()).toBe(false);
        expect(routerPushMock).toHaveBeenLastCalledWith({ path: "/tools/list" });
        expect(fetchToolsMock).toHaveBeenLastCalledWith("");
    });

    it("helps recover from empty results and hides the empty state while loading", async () => {
        const toolStore = useToolStore();
        const wrapper = mount(ToolsList as object, { localVue, pinia, router, propsData: { owner: "missing" } });
        await flushPromises();
        expect(wrapper.text()).toContain("No tools match your search.");
        toolStore.loading = true;
        await flushPromises();
        expect(wrapper.text()).not.toContain("No tools match your search.");
        toolStore.loading = false;
        await flushPromises();
        const reset = wrapper.findAll("button").find((button) => button.text() === "Clear filters and show all tools")!;
        await reset.trigger("click");
        await flushPromises();
        expect(wrapper.text()).not.toContain("No tools match your search.");
        expect(wrapper.findComponent(ToolsListTable).exists()).toBe(true);
        expect(routerPushMock).toHaveBeenLastCalledWith({ path: "/tools/list" });
    });

    it("keeps the ontology chip visible during ontology search and removes only that filter", async () => {
        const toolStore = useToolStore();
        toolStore.toolSections["ontology:edam_operations"] = {
            operation_1: { id: "operation_1", name: "Quality control", model_class: "ToolSection", tools: ["fastqc"] },
        };
        const wrapper = mount(ToolsList as object, {
            localVue,
            pinia,
            router,
            propsData: { ontology: '"operation_1"', tag: ["data cleanup"] },
        });
        await flushPromises();
        await wrapper.get(".tool-section-dropdown button.dropdown-toggle").trigger("click");
        await wrapper.get('input[aria-label="Search ontologies"]').setValue("unrelated search");
        const chip = wrapper.get('button[title="Remove ontology Quality control"]');
        expect(chip.classes()).toContain("g-outline");
        await chip.trigger("click");
        await flushPromises();
        expect(wrapper.find('button[title="Remove ontology Quality control"]').exists()).toBe(false);
        expect(routerPushMock).toHaveBeenLastCalledWith({ path: "/tools/list", query: { tag: ["data cleanup"] } });
    });

    it("populates the selector from the tag mapping even if cached tools have no tags", async () => {
        const toolStore = useToolStore();
        toolStore.saveAllTools([{ id: "fastqc", name: "FastQC" } as Tool]);
        toolStore.toolTagsById = { uncached_tool: ["Quality Control", "Get Data"] };
        const wrapper = mount(ToolsList as object, { localVue, pinia, router });
        await flushPromises();
        expect(wrapper.findComponent(ToolsListTagFilter).props("tags")).toEqual(["Get Data", "Quality Control"]);
    });

    it("synchronizes tag selection and removal with search text, URL, and backend queries", async () => {
        const wrapper = mount(ToolsList as object, {
            localVue,
            pinia,
            router,
            propsData: { owner: "devteam" },
        });
        await flushPromises();
        const selector = wrapper.findComponent(ToolsListTagFilter);
        selector.vm.$emit("toggle-tag", "data cleanup");
        await flushPromises();
        expect(selector.props("selectedTags")).toEqual(["data cleanup"]);
        expect(routerPushMock).toHaveBeenLastCalledWith({
            path: "/tools/list",
            query: { owner: "devteam", tag: ["data cleanup"] },
        });
        expect(fetchToolsMock).toHaveBeenLastCalledWith('(owner:(devteam) AND tool_tags:("data cleanup"))');

        selector.vm.$emit("toggle-tag", "data cleanup");
        await flushPromises();
        expect(selector.props("selectedTags")).toEqual([]);
        expect(routerPushMock).toHaveBeenLastCalledWith({ path: "/tools/list", query: { owner: "devteam" } });
        expect(fetchToolsMock).toHaveBeenLastCalledWith("(owner:(devteam))");
    });

    it("performs an advanced search with a router push", async () => {
        const wrapper = mount(ToolsList as object, {
            global: {
                ...localVue,
                plugins: [...(localVue.plugins ?? []), pinia],
            },
        });

        // By default, no search text, fetch tools is still called but without a query
        expect(fetchToolsMock).toHaveBeenCalledWith("");

        expect(wrapper.find("[data-description='toggle advanced search']").exists()).toBe(true);

        await wrapper.find("[data-description='toggle advanced search']").trigger("click");

        expect(wrapper.find("[data-description='advanced filters']").exists()).toBe(true);

        // Now add all filters in the advanced menu. BFormInput isn't stubbed, so
        // `find()` here returns the real <input> DOM element, not a component wrapper.
        for (const [selector, value] of Object.entries(FILTER_INPUTS)) {
            const filterInput = wrapper.find(selector);
            expect(filterInput.exists()).toBe(true);
            expect(filterInput.attributes("type")).toBe("text");
            await filterInput.setValue(value);
        }

        // Test: we route to the list with filters
        await wrapper.find("[data-description='apply filters']").trigger("click");

        expect(routerPushMock).toHaveBeenCalledWith({
            path: "/tools/list",
            query: FILTER_SETTINGS,
        });
    });

    it("detects filters in the route and searches the backend", async () => {
        mount(ToolsList as object, {
            global: {
                ...localVue,
                plugins: [...(localVue.plugins ?? []), pinia],
            },
            props: FILTER_SETTINGS,
        });

        expect(fetchToolsMock).toHaveBeenCalledWith(WHOOSH_QUERY);
    });

    it("detects repeated tag filters in the route and searches the backend", async () => {
        mount(ToolsList as object, {
            localVue,
            pinia,
            router,
            propsData: TAG_FILTER_SETTINGS,
        });

        expect(fetchToolsMock).toHaveBeenCalledWith(TAG_WHOOSH_QUERY);
    });

    it("emits repeated tag filters to the router query", async () => {
        vi.useFakeTimers();

        const wrapper = mount(ToolsList as object, {
            localVue,
            pinia,
            router,
        });

        routerPushMock.mockClear();

        const input = wrapper.find("input.search-query");
        await input.setValue('tag:collection_ops tag:"data cleanup"');
        vi.advanceTimersByTime(400);
        await flushPromises();

        expect(routerPushMock).toHaveBeenLastCalledWith({
            path: "/tools/list",
            query: TAG_FILTER_SETTINGS,
        });
        expect(fetchToolsMock).toHaveBeenLastCalledWith(TAG_WHOOSH_QUERY);
    });

    it("autocompletes multi-word tags in the main search bar", async () => {
        vi.useFakeTimers();

        const wrapper = mount(ToolsList as object, {
            localVue,
            pinia,
            router,
        });

        routerPushMock.mockClear();

        const input = wrapper.find("input.search-query");
        await input.setValue("tag:dat");
        await flushPromises();

        const suggestions = wrapper.find("[data-description='search-autocomplete']");
        expect(suggestions.exists()).toBe(true);
        expect(suggestions.text()).toContain('tag:"data cleanup"');

        await suggestions.find("button").trigger("mousedown");
        await flushPromises();

        expect((input.element as HTMLInputElement).value).toBe('tag:"data cleanup" ');

        vi.advanceTimersByTime(400);
        await flushPromises();

        expect(routerPushMock).toHaveBeenLastCalledWith({
            path: "/tools/list",
            query: { tag: ["data cleanup"] },
        });
        expect(fetchToolsMock).toHaveBeenLastCalledWith('(tool_tags:("data cleanup"))');
    });

    it("does not re-open autocomplete for a complete multi-word tag missing only the closing quote", async () => {
        vi.useFakeTimers();

        const wrapper = mount(ToolsList as object, {
            localVue,
            pinia,
            router,
        });

        const input = wrapper.find("input.search-query");
        await input.setValue('tag:"data cleanup');
        await flushPromises();

        expect(wrapper.find("[data-description='search-autocomplete']").exists()).toBe(false);

        await input.trigger("keydown", { key: "Enter" });
        await flushPromises();

        expect((input.element as HTMLInputElement).value).toBe('tag:"data cleanup');
    });

    it("quotes multi-word tag filters when a tool card tag is clicked", async () => {
        vi.useFakeTimers();

        const wrapper = mount(ToolsList as object, {
            localVue,
            pinia,
            router,
        });

        routerPushMock.mockClear();

        wrapper.findComponent(ToolsListTable).vm.$emit("apply-filter", "tag", "data cleanup");
        await flushPromises();

        const input = wrapper.find("input.search-query");
        expect((input.element as HTMLInputElement).value).toBe('tag:"data cleanup"');

        vi.advanceTimersByTime(400);
        await flushPromises();

        expect(routerPushMock).toHaveBeenLastCalledWith({
            path: "/tools/list",
            query: { tag: ["data cleanup"] },
        });
        expect(fetchToolsMock).toHaveBeenLastCalledWith('(tool_tags:("data cleanup"))');
    });

    it("renders route-provided multi-word tags with quotes in the search bar", async () => {
        const wrapper = mount(ToolsList as object, {
            localVue,
            pinia,
            router,
            propsData: { tag: ["data cleanup"] },
        });

        await flushPromises();

        const input = wrapper.find("input.search-query");
        expect((input.element as HTMLInputElement).value).toBe('tag:"data cleanup"');
    });

    it("treats legacy ?section= URLs as tag filters for backwards compatibility", async () => {
        // Old links from before the section-to-tag migration shouldn't render an
        // empty page. We fold `section=Get Data` into the tag filter; if no tag
        // exists with that name the result is empty (same as today), otherwise
        // the link keeps working.
        const wrapper = mount(ToolsList as object, {
            localVue,
            pinia,
            router,
            propsData: { section: "Get Data" },
        });

        await flushPromises();

        const input = wrapper.find("input.search-query");
        expect((input.element as HTMLInputElement).value).toBe('tag:"Get Data"');
    });

    it("passes explicit boolean tag expressions through as raw search", async () => {
        vi.useFakeTimers();

        const wrapper = mount(ToolsList as object, {
            localVue,
            pinia,
            router,
        });

        routerPushMock.mockClear();

        const input = wrapper.find("input.search-query");
        await input.setValue(RAW_TAG_SEARCH);
        vi.advanceTimersByTime(400);
        await flushPromises();

        expect(routerPushMock).toHaveBeenLastCalledWith({
            path: "/tools/list",
            query: { search: RAW_TAG_SEARCH },
        });
        expect(fetchToolsMock).toHaveBeenLastCalledWith(RAW_TAG_WHOOSH_QUERY);
    });

    it("preserves mixed quoted-tag and free-text input as raw search text", async () => {
        vi.useFakeTimers();

        const wrapper = mount(ToolsList as object, {
            localVue,
            pinia,
            router,
        });

        routerPushMock.mockClear();

        const input = wrapper.find("input.search-query");
        await input.setValue(MIXED_TAG_SEARCH);
        vi.advanceTimersByTime(400);
        await flushPromises();

        expect(routerPushMock).toHaveBeenLastCalledWith({
            path: "/tools/list",
            query: { search: MIXED_TAG_SEARCH },
        });
        expect(fetchToolsMock).toHaveBeenLastCalledWith(MIXED_TAG_WHOOSH_QUERY);
    });

    it("translates mixed tag and ontology search into a valid whoosh query", async () => {
        vi.useFakeTimers();

        const wrapper = mount(ToolsList as object, {
            localVue,
            pinia,
            router,
        });

        routerPushMock.mockClear();

        const input = wrapper.find("input.search-query");
        await input.setValue(MIXED_TAG_AND_ONTOLOGY_SEARCH);
        vi.advanceTimersByTime(400);
        await flushPromises();

        expect(routerPushMock).toHaveBeenLastCalledWith({
            path: "/tools/list",
            query: MIXED_TAG_AND_ONTOLOGY_FILTER_SETTINGS,
        });
        expect(fetchToolsMock).toHaveBeenLastCalledWith(MIXED_TAG_AND_ONTOLOGY_WHOOSH_QUERY);
    });
});
