import { createTestingPinia } from "@pinia/testing";
import { getFakePageSummary } from "@tests/test-data/pages";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { HistoryPageSummary } from "@/api/pages";

import { FAKE_PAGE_SUMMARY, FAKE_PAGE_UNTITLED } from "./testData";

import PageCard from "./PageCard.vue";

enableAutoUnmount(afterEach);

function mountPageCard(page: HistoryPageSummary = FAKE_PAGE_SUMMARY) {
    // Render GCard so the title, badges, and action controls remain covered.
    return mount(PageCard as object, {
        props: { page: getFakePageSummary({ ...page, revision_ids: [...page.revision_ids] }) },
        global: withPlugins(getLocalVue(), createTestingPinia({ createSpy: vi.fn })),
    });
}

const SELECTORS = {
    title: `#g-card-title-link-page-${FAKE_PAGE_SUMMARY.id}`,
    revision: `#g-card-badge-notebook-revisions-count-page-${FAKE_PAGE_SUMMARY.id}`,
    time: `#g-card-page-${FAKE_PAGE_SUMMARY.id}-update-time`,
    view: `#g-card-action-view-notebook-page-${FAKE_PAGE_SUMMARY.id}`,
    edit: `#g-card-action-edit-notebook-page-${FAKE_PAGE_SUMMARY.id}`,
};

describe("PageCard", () => {
    it("displays the page title and emits edit when clicked", async () => {
        const wrapper = mountPageCard();
        const title = wrapper.find(SELECTORS.title);
        expect(title.text()).toBe("My Analysis");
        expect(title.attributes("title")).toBe("Edit Notebook");

        await title.trigger("click");
        expect(wrapper.emitted("edit")).toEqual([[]]);
    });

    it("shows 'Untitled Notebook' when title is empty", () => {
        const wrapper = mountPageCard(FAKE_PAGE_UNTITLED);
        const title = wrapper.find(`#g-card-title-link-page-${FAKE_PAGE_UNTITLED.id}`);
        expect(title.text()).toBe("Untitled Notebook");
    });

    it("displays the update time badge and single revision", () => {
        const wrapper = mountPageCard();
        expect(wrapper.find(SELECTORS.time).exists()).toBe(true);
        expect(wrapper.find(SELECTORS.revision).text()).toBe("1 Revision");
    });

    it("emits view when the View action is clicked", async () => {
        const wrapper = mountPageCard();
        await wrapper.find(SELECTORS.view).trigger("click");
        expect(wrapper.emitted("view")).toEqual([[]]);
    });

    it("emits edit when the Edit action is clicked", async () => {
        const wrapper = mountPageCard();
        await wrapper.find(SELECTORS.edit).trigger("click");
        expect(wrapper.emitted("edit")).toEqual([[]]);
    });
});
