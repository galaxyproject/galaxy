import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, suppressBootstrapVueWarnings } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import VueRouter from "vue-router";

import type * as HistoriesApi from "@/api/histories";
import { getMyHistories } from "@/api/histories";
import { type Tool, useToolStore } from "@/stores/toolStore";

import HistoryList from "./HistoryList.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";

vi.mock("@/api/histories", async (importOriginal) => {
    const actual = await importOriginal<typeof HistoriesApi>();
    return {
        ...actual,
        getMyHistories: vi.fn(),
        getSharedHistories: vi.fn(),
        getPublishedHistories: vi.fn(),
        getArchivedHistories: vi.fn(),
    };
});

const mockedGetMyHistories = getMyHistories as ReturnType<typeof vi.fn>;

const localVue = getLocalVue();
localVue.use(VueRouter);
const router = new VueRouter();

async function mountHistoryList() {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);

    useToolStore().saveAllTools([
        { id: "cut1", name: "Cut" },
        { id: "adv_cut1", name: "Advanced Cut" },
        { id: "cat1", name: "Concatenate datasets" },
    ] as unknown as Tool[]);

    const wrapper = mount(HistoryList as object, {
        localVue,
        pinia,
        router,
    });

    await flushPromises();

    return wrapper;
}

/** Simulates a user typing `filterText` into the filter box and waits for the resulting `load()` call. */
async function search(wrapper: ReturnType<typeof mount>, filterText: string) {
    const filterMenu = wrapper.findComponent(FilterMenu);
    filterMenu.vm.$emit("update:filter-text", filterText);
    await flushPromises();
}

/** Returns the `search` value most recently sent to the backend via `getMyHistories`. */
function lastSearchSent() {
    const lastCall = mockedGetMyHistories.mock.calls[mockedGetMyHistories.mock.calls.length - 1];
    return lastCall?.[0]?.search;
}

describe("HistoryList filtering", () => {
    beforeEach(() => {
        suppressBootstrapVueWarnings();
        vi.clearAllMocks();
        mockedGetMyHistories.mockResolvedValue({ data: [], total: 0 });
    });

    it("sends a plain-text search as-is", async () => {
        const wrapper = await mountHistoryList();

        await search(wrapper, "my history name");

        expect(lastSearchSent()).toBe("my history name");
    });

    it("sends a name: filter as-is", async () => {
        const wrapper = await mountHistoryList();

        await search(wrapper, "name:'My History'");

        expect(lastSearchSent()).toBe("name:'My History'");
    });

    it("sends a tag: filter as-is", async () => {
        const wrapper = await mountHistoryList();

        await search(wrapper, "tag:'my-tag'");

        expect(lastSearchSent()).toBe("tag:'my-tag'");
    });

    it("sends a tool_id: filter as-is", async () => {
        const wrapper = await mountHistoryList();

        await search(wrapper, "tool_id:cut1");

        expect(lastSearchSent()).toBe("tool_id:cut1");
    });

    it("resolves a tool_name: filter to the matching tool_id before sending", async () => {
        const wrapper = await mountHistoryList();

        await search(wrapper, "tool_name:'Cut'");

        const sent = lastSearchSent();
        expect(sent).toContain("tool_id:cut1");
        expect(sent).not.toContain("tool_name");
    });

    it("does not resolve tool_name to tool_id when no tool matches", async () => {
        const wrapper = await mountHistoryList();

        await search(wrapper, "tool_name:'nonexistent tool'");

        const sent = lastSearchSent();
        expect(sent).not.toContain("tool_id:");
        expect(sent).toContain("tool_name");
    });

    it("combines multiple filters into one search string", async () => {
        const wrapper = await mountHistoryList();

        await search(wrapper, "name:'My History' tag:'my-tag'");

        const sent = lastSearchSent();
        expect(sent).toContain("name:'My History'");
        expect(sent).toContain("tag:'my-tag'");
    });
});
