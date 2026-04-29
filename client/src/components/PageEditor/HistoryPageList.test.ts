import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it } from "vitest";

import type { HistoryPageSummary } from "@/api/pages";

import HistoryPageList from "./HistoryPageList.vue";

const localVue = getLocalVue();

const FAKE_PAGE_SUMMARY: HistoryPageSummary = {
    id: "page-1",
    history_id: "history-1",
    title: "My Analysis",
    slug: null,
    source_invocation_id: null,
    published: false,
    importable: false,
    deleted: false,
    latest_revision_id: "rev-1",
    revision_ids: ["rev-1"],
    create_time: "2025-06-15T10:30:00Z",
    update_time: "2025-06-15T12:45:00Z",
    username: "test",
    email_hash: "",
    author_deleted: false,
    model_class: "Page",
    tags: [],
};

const FAKE_PAGE_UNTITLED: HistoryPageSummary = {
    ...FAKE_PAGE_SUMMARY,
    id: "page-2",
    title: "",
};

const SELECTORS = {
    HEADER_TITLE: "h4",
    NEW_BUTTON: "bbutton-stub",
    EMPTY_STATE: ".empty-state",
    PAGE_ITEMS: ".page-items",
    PAGE_ITEM: ".page-item",
    PAGE_TITLE: ".page-title",
    PAGE_META: ".page-meta",
    VIEW_BUTTON: "[data-description='page view button']",
};

async function mountComponent(propsData: { pages: HistoryPageSummary[] }) {
    const wrapper = shallowMount(HistoryPageList as object, {
        localVue,
        propsData,
    });
    await flushPromises();
    return wrapper;
}

describe("HistoryPageList", () => {
    describe("Header", () => {
        let wrapper: Wrapper<Vue>;

        beforeEach(async () => {
            wrapper = await mountComponent({ pages: [] });
        });

        it("always shows 'Galaxy Notebooks' heading", () => {
            const heading = wrapper.find(SELECTORS.HEADER_TITLE);
            expect(heading.exists()).toBe(true);
            expect(heading.text()).toBe("Galaxy Notebooks");
        });

        it("always shows 'New Notebook' button", () => {
            const button = wrapper.find(SELECTORS.NEW_BUTTON);
            expect(button.exists()).toBe(true);
            expect(button.text()).toContain("New Notebook");
        });
    });

    describe("Empty state", () => {
        let wrapper: Wrapper<Vue>;

        beforeEach(async () => {
            wrapper = await mountComponent({ pages: [] });
        });

        it("shows 'No notebooks yet' when pages prop is empty array", () => {
            const emptyState = wrapper.find(SELECTORS.EMPTY_STATE);
            expect(emptyState.exists()).toBe(true);
            expect(emptyState.text()).toContain("No notebooks yet");
        });

        it("shows create guidance text when no pages", () => {
            const emptyState = wrapper.find(SELECTORS.EMPTY_STATE);
            expect(emptyState.text()).toContain("Create a notebook to document your analysis");
        });

        it("does NOT show page items when empty", () => {
            expect(wrapper.find(SELECTORS.PAGE_ITEMS).exists()).toBe(false);
        });
    });

    describe("Page list", () => {
        let wrapper: Wrapper<Vue>;

        beforeEach(async () => {
            wrapper = await mountComponent({
                pages: [FAKE_PAGE_SUMMARY, FAKE_PAGE_UNTITLED],
            });
        });

        it("renders each page as a clickable item", () => {
            const items = wrapper.findAll(SELECTORS.PAGE_ITEM);
            expect(items.length).toBe(2);
        });

        it("displays page title for each item", () => {
            const titles = wrapper.findAll(SELECTORS.PAGE_TITLE);
            expect(titles.at(0).text()).toBe("My Analysis");
        });

        it("shows 'Untitled Notebook' when title is empty", () => {
            const titles = wrapper.findAll(SELECTORS.PAGE_TITLE);
            expect(titles.at(1).text()).toBe("Untitled Notebook");
        });

        it("displays formatted update_time for each page", () => {
            const meta = wrapper.findAll(SELECTORS.PAGE_META);
            const metaText = meta.at(0).text();
            expect(metaText).toContain("Updated");
            expect(metaText.replace("Updated", "").trim().length).toBeGreaterThan(0);
        });

        it("does NOT show empty state when pages exist", () => {
            expect(wrapper.find(SELECTORS.EMPTY_STATE).exists()).toBe(false);
        });
    });

    describe("Events", () => {
        it("emits 'create' when New Page button is clicked", async () => {
            const wrapper = await mountComponent({ pages: [] });
            const button = wrapper.find(SELECTORS.NEW_BUTTON);
            await button.trigger("click");
            expect(wrapper.emitted().create).toBeTruthy();
        });

        it("emits 'select' with page.id when a page item is clicked", async () => {
            const wrapper = await mountComponent({
                pages: [FAKE_PAGE_SUMMARY],
            });
            const item = wrapper.find(SELECTORS.PAGE_ITEM);
            await item.trigger("click");
            expect(wrapper.emitted().select).toBeTruthy();
            expect(wrapper.emitted().select![0]![0]).toBe("page-1");
        });
    });

    describe("View button", () => {
        it("shows view button on each page item", async () => {
            const wrapper = await mountComponent({
                pages: [FAKE_PAGE_SUMMARY],
            });
            const viewButton = wrapper.find(SELECTORS.VIEW_BUTTON);
            expect(viewButton.exists()).toBe(true);
        });

        it("emits 'view' with page.id when view button clicked", async () => {
            const wrapper = await mountComponent({
                pages: [FAKE_PAGE_SUMMARY],
            });
            const viewButton = wrapper.find(SELECTORS.VIEW_BUTTON);
            await viewButton.trigger("click");
            expect(wrapper.emitted().view).toBeTruthy();
            expect(wrapper.emitted().view![0]![0]).toBe("page-1");
        });

        it("does not emit 'select' when view button clicked", async () => {
            const wrapper = await mountComponent({
                pages: [FAKE_PAGE_SUMMARY],
            });
            const viewButton = wrapper.find(SELECTORS.VIEW_BUTTON);
            await viewButton.trigger("click");
            expect(wrapper.emitted().select).toBeFalsy();
        });
    });
});
