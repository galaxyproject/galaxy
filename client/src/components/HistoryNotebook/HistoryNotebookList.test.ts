import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it } from "vitest";

import type { HistoryNotebookSummary } from "@/api/historyNotebooks";

import HistoryNotebookList from "./HistoryNotebookList.vue";

const localVue = getLocalVue();

const FAKE_NOTEBOOK_SUMMARY: HistoryNotebookSummary = {
    id: "notebook-1",
    history_id: "history-1",
    title: "My Analysis",
    latest_revision_id: "rev-1",
    revision_ids: ["rev-1"],
    deleted: false,
    create_time: "2025-06-15T10:30:00Z",
    update_time: "2025-06-15T12:45:00Z",
};

const FAKE_NOTEBOOK_UNTITLED: HistoryNotebookSummary = {
    ...FAKE_NOTEBOOK_SUMMARY,
    id: "notebook-2",
    title: null,
};

const SELECTORS = {
    HEADER_TITLE: "h4",
    NEW_BUTTON: "bbutton-stub",
    EMPTY_STATE: ".empty-state",
    NOTEBOOK_ITEMS: ".notebook-items",
    NOTEBOOK_ITEM: ".notebook-item",
    NOTEBOOK_TITLE: ".notebook-title",
    NOTEBOOK_META: ".notebook-meta",
    VIEW_BUTTON: "[data-description='notebook view button']",
};

async function mountComponent(propsData: { notebooks: HistoryNotebookSummary[] }) {
    const wrapper = shallowMount(HistoryNotebookList as object, {
        localVue,
        propsData,
    });
    await flushPromises();
    return wrapper;
}

describe("HistoryNotebookList", () => {
    describe("Header", () => {
        let wrapper: Wrapper<Vue>;

        beforeEach(async () => {
            wrapper = await mountComponent({ notebooks: [] });
        });

        it("always shows 'Notebooks' heading", () => {
            const heading = wrapper.find(SELECTORS.HEADER_TITLE);
            expect(heading.exists()).toBe(true);
            expect(heading.text()).toBe("Notebooks");
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
            wrapper = await mountComponent({ notebooks: [] });
        });

        it("shows 'No notebooks yet' when notebooks prop is empty array", () => {
            const emptyState = wrapper.find(SELECTORS.EMPTY_STATE);
            expect(emptyState.exists()).toBe(true);
            expect(emptyState.text()).toContain("No notebooks yet");
        });

        it("shows create guidance text when no notebooks", () => {
            const emptyState = wrapper.find(SELECTORS.EMPTY_STATE);
            expect(emptyState.text()).toContain("Create a notebook to document your analysis");
        });

        it("does NOT show notebook items when empty", () => {
            expect(wrapper.find(SELECTORS.NOTEBOOK_ITEMS).exists()).toBe(false);
        });
    });

    describe("Notebook list", () => {
        let wrapper: Wrapper<Vue>;

        beforeEach(async () => {
            wrapper = await mountComponent({
                notebooks: [FAKE_NOTEBOOK_SUMMARY, FAKE_NOTEBOOK_UNTITLED],
            });
        });

        it("renders each notebook as a clickable item", () => {
            const items = wrapper.findAll(SELECTORS.NOTEBOOK_ITEM);
            expect(items.length).toBe(2);
        });

        it("displays notebook title for each item", () => {
            const titles = wrapper.findAll(SELECTORS.NOTEBOOK_TITLE);
            expect(titles.at(0).text()).toBe("My Analysis");
        });

        it("shows 'Untitled Notebook' when title is null", () => {
            const titles = wrapper.findAll(SELECTORS.NOTEBOOK_TITLE);
            expect(titles.at(1).text()).toBe("Untitled Notebook");
        });

        it("displays formatted update_time for each notebook", () => {
            const meta = wrapper.findAll(SELECTORS.NOTEBOOK_META);
            const metaText = meta.at(0).text();
            expect(metaText).toContain("Updated");
            // Verify a formatted date follows "Updated " (locale-independent check)
            expect(metaText.replace("Updated", "").trim().length).toBeGreaterThan(0);
        });

        it("does NOT show empty state when notebooks exist", () => {
            expect(wrapper.find(SELECTORS.EMPTY_STATE).exists()).toBe(false);
        });
    });

    describe("Events", () => {
        it("emits 'create' when New Notebook button is clicked", async () => {
            const wrapper = await mountComponent({ notebooks: [] });
            const button = wrapper.find(SELECTORS.NEW_BUTTON);
            await button.trigger("click");
            expect(wrapper.emitted().create).toBeTruthy();
        });

        it("emits 'select' with notebook.id when a notebook item is clicked", async () => {
            const wrapper = await mountComponent({
                notebooks: [FAKE_NOTEBOOK_SUMMARY],
            });
            const item = wrapper.find(SELECTORS.NOTEBOOK_ITEM);
            await item.trigger("click");
            expect(wrapper.emitted().select).toBeTruthy();
            expect(wrapper.emitted().select![0]![0]).toBe("notebook-1");
        });
    });

    describe("View button", () => {
        it("shows view button on each notebook item", async () => {
            const wrapper = await mountComponent({
                notebooks: [FAKE_NOTEBOOK_SUMMARY],
            });
            const viewButton = wrapper.find(SELECTORS.VIEW_BUTTON);
            expect(viewButton.exists()).toBe(true);
        });

        it("emits 'view' with notebook.id when view button clicked", async () => {
            const wrapper = await mountComponent({
                notebooks: [FAKE_NOTEBOOK_SUMMARY],
            });
            const viewButton = wrapper.find(SELECTORS.VIEW_BUTTON);
            await viewButton.trigger("click");
            expect(wrapper.emitted().view).toBeTruthy();
            expect(wrapper.emitted().view![0]![0]).toBe("notebook-1");
        });

        it("does not emit 'select' when view button clicked", async () => {
            const wrapper = await mountComponent({
                notebooks: [FAKE_NOTEBOOK_SUMMARY],
            });
            const viewButton = wrapper.find(SELECTORS.VIEW_BUTTON);
            await viewButton.trigger("click");
            expect(wrapper.emitted().select).toBeFalsy();
        });
    });
});
