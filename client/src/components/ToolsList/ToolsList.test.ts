import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import toolsListUntyped from "@/components/ToolsView/testData/toolsList.json";
import type { Tool } from "@/stores/toolStore";
import { useToolStore } from "@/stores/toolStore";

import ToolsList from "./ToolsList.vue";
import ToolsListTable from "./ToolsListTable.vue";

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
// option to render — keep both wired up.
vi.mock("vue-router/composables", () => ({
    useRouter: () => ({
        push: routerPushMock,
    }),
}));

const localVue = getLocalVue();
const router = injectTestRouter(localVue);

function toToolsById(list: Tool[]) {
    return list.reduce(
        (acc, tool) => {
            acc[tool.id] = tool;
            return acc;
        },
        {} as Record<string, Tool>,
    );
}

describe("ToolsList", () => {
    let fetchToolsMock: ReturnType<typeof vi.spyOn>;
    let pinia: ReturnType<typeof createTestingPinia>;

    beforeEach(() => {
        pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        setActivePinia(pinia);

        const toolStore = useToolStore(pinia);
        toolStore.toolsById = toToolsById(toolsList);
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

    it("performs an advanced search with a router push", async () => {
        const wrapper = mount(ToolsList as object, {
            localVue,
            pinia,
            router,
        });

        // By default, no search text, fetch tools is still called but without a query
        expect(fetchToolsMock).toHaveBeenCalledWith("");

        expect(wrapper.find("[data-description='toggle advanced search']").exists()).toBe(true);

        await wrapper.find("[data-description='toggle advanced search']").trigger("click");

        expect(wrapper.find("[data-description='advanced filters']").exists()).toBe(true);

        // Now add all filters in the advanced menu
        for (const [selector, value] of Object.entries(FILTER_INPUTS)) {
            const filterInput = wrapper.find(selector);
            expect(filterInput.vm).toBeTruthy();
            expect(filterInput.props().type).toBe("text");
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
            localVue,
            pinia,
            router,
            propsData: FILTER_SETTINGS,
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
