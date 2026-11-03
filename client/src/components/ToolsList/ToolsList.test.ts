import { createTestingPinia } from "@pinia/testing";
import { getFakeTool } from "@tests/test-data/tools";
import { createTestRouter, getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { disposePinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import type * as VueRouter from "vue-router";

import toolsListUntyped from "@/components/ToolsView/testData/toolsList.json";
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
const toolsList = toolsListUntyped.map((tool) => {
    // JSON imports widen the empty-string hidden flag to string.
    if (tool.hidden !== "" && typeof tool.hidden !== "boolean") {
        throw new Error(`Invalid hidden flag in tool fixture: ${tool.id}`);
    }
    return getFakeTool({ ...tool, hidden: tool.hidden });
});

const routerPushMock = vi.fn();

// Keep real router exports for mounted RouterLinks while observing useRouter pushes.
vi.mock("vue-router", async (importOriginal) => {
    const actual = await importOriginal<typeof VueRouter>();
    return {
        ...actual,
        useRouter: () => ({
            push: routerPushMock,
        }),
    };
});

const localVue = getLocalVue();
const router = createTestRouter();

describe("ToolsList", () => {
    let fetchToolsMock: ReturnType<typeof useToolStore>["fetchTools"];
    let pinia: ReturnType<typeof createTestingPinia>;

    beforeEach(() => {
        pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        const ownedPinia = pinia;
        onTestFinished(() => disposePinia(ownedPinia));
        setActivePinia(pinia);

        const toolStore = useToolStore(pinia);
        toolStore.toolsById = Object.fromEntries(toolsList.map((tool) => [tool.id, tool]));
        fetchToolsMock = vi.spyOn(toolStore, "fetchTools").mockResolvedValue();
        vi.spyOn(toolStore, "fetchToolSections").mockResolvedValue();
        vi.spyOn(toolStore, "fetchToolTagsMapping").mockResolvedValue();
        vi.spyOn(toolStore, "fetchHelpForId").mockResolvedValue();

        // Clear the router mock between tests
        routerPushMock.mockClear();
    });

    afterEach(() => {
        if (vi.isFakeTimers()) {
            vi.clearAllTimers();
        }
        vi.useRealTimers();
        vi.restoreAllMocks();
        routerPushMock.mockClear();
    });
    enableAutoUnmount(afterEach);
    afterEach(async () => {
        // Settle child/store work before unmounting and disposing the stores it uses.
        await flushPromises();
    });

    function mountToolsList(props: InstanceType<typeof ToolsList>["$props"] = {}) {
        return mount(ToolsList, {
            global: withPlugins(localVue, pinia, router),
            props,
        });
    }

    it("performs an advanced search with a router push", async () => {
        const wrapper = mountToolsList();

        // By default, no search text, fetch tools is still called but without a query
        expect(fetchToolsMock).toHaveBeenCalledWith("");

        expect(wrapper.find("[data-description='toggle advanced search']").exists()).toBe(true);

        await wrapper.get("[data-description='toggle advanced search']").trigger("click");

        expect(wrapper.find("[data-description='advanced filters']").exists()).toBe(true);

        // Now add all filters in the advanced menu. BFormInput isn't stubbed, so
        // `find()` here returns the real <input> DOM element, not a component wrapper.
        for (const [selector, value] of Object.entries(FILTER_INPUTS)) {
            const filterInput = wrapper.find<HTMLInputElement>(selector);
            expect(filterInput.exists()).toBe(true);
            expect(filterInput.attributes("type")).toBe("text");
            await filterInput.setValue(value);
        }

        // Test: we route to the list with filters
        await wrapper.get("[data-description='apply filters']").trigger("click");

        expect(routerPushMock).toHaveBeenCalledWith({
            path: "/tools/list",
            query: FILTER_SETTINGS,
        });
    });

    it("detects filters in the route and searches the backend", async () => {
        mountToolsList(FILTER_SETTINGS);

        expect(fetchToolsMock).toHaveBeenCalledWith(WHOOSH_QUERY);
    });

    it("detects repeated tag filters in the route and searches the backend", async () => {
        mountToolsList(TAG_FILTER_SETTINGS);

        expect(fetchToolsMock).toHaveBeenCalledWith(TAG_WHOOSH_QUERY);
    });

    it("emits repeated tag filters to the router query", async () => {
        vi.useFakeTimers();

        const wrapper = mountToolsList();

        routerPushMock.mockClear();

        const input = wrapper.get<HTMLInputElement>("input.search-query");
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

        const wrapper = mountToolsList();

        routerPushMock.mockClear();

        const input = wrapper.get<HTMLInputElement>("input.search-query");
        await input.setValue("tag:dat");
        await flushPromises();

        const suggestions = wrapper.find("[data-description='search-autocomplete']");
        expect(suggestions.exists()).toBe(true);
        expect(suggestions.text()).toContain('tag:"data cleanup"');

        await suggestions.find("button").trigger("mousedown");
        await flushPromises();

        expect(input.element.value).toBe('tag:"data cleanup" ');

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

        const wrapper = mountToolsList();

        const input = wrapper.get<HTMLInputElement>("input.search-query");
        await input.setValue('tag:"data cleanup');
        await flushPromises();

        expect(wrapper.find("[data-description='search-autocomplete']").exists()).toBe(false);

        await input.trigger("keydown", { key: "Enter" });
        await flushPromises();

        expect(input.element.value).toBe('tag:"data cleanup');
    });

    it("quotes multi-word tag filters when a tool card tag is clicked", async () => {
        vi.useFakeTimers();

        const wrapper = mountToolsList();

        routerPushMock.mockClear();

        wrapper.getComponent(ToolsListTable).vm.$emit("apply-filter", "tag", "data cleanup");
        await flushPromises();

        const input = wrapper.get<HTMLInputElement>("input.search-query");
        expect(input.element.value).toBe('tag:"data cleanup"');

        vi.advanceTimersByTime(400);
        await flushPromises();

        expect(routerPushMock).toHaveBeenLastCalledWith({
            path: "/tools/list",
            query: { tag: ["data cleanup"] },
        });
        expect(fetchToolsMock).toHaveBeenLastCalledWith('(tool_tags:("data cleanup"))');
    });

    it("renders route-provided multi-word tags with quotes in the search bar", async () => {
        const wrapper = mountToolsList({ tag: ["data cleanup"] });

        await flushPromises();

        const input = wrapper.get<HTMLInputElement>("input.search-query");
        expect(input.element.value).toBe('tag:"data cleanup"');
    });

    it("treats legacy ?section= URLs as tag filters for backwards compatibility", async () => {
        // Old links from before the section-to-tag migration shouldn't render an
        // empty page. We fold `section=Get Data` into the tag filter; if no tag
        // exists with that name the result is empty (same as today), otherwise
        // the link keeps working.
        const wrapper = mountToolsList({ section: "Get Data" });

        await flushPromises();

        const input = wrapper.get<HTMLInputElement>("input.search-query");
        expect(input.element.value).toBe('tag:"Get Data"');
    });

    it("passes explicit boolean tag expressions through as raw search", async () => {
        vi.useFakeTimers();

        const wrapper = mountToolsList();

        routerPushMock.mockClear();

        const input = wrapper.get<HTMLInputElement>("input.search-query");
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

        const wrapper = mountToolsList();

        routerPushMock.mockClear();

        const input = wrapper.get<HTMLInputElement>("input.search-query");
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

        const wrapper = mountToolsList();

        routerPushMock.mockClear();

        const input = wrapper.get<HTMLInputElement>("input.search-query");
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
