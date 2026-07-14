import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { FAKE_PAGE_SUMMARY, FAKE_PAGE_UNTITLED } from "./testData";

import PageCard from "./PageCard.vue";

const localVue = getLocalVue();

function getSelector(selector: "title" | "revision" | "time" | "view" | "edit", pageId: string) {
    if (selector === "title") {
        return `#g-card-title-link-page-${pageId}`;
    } else if (selector === "revision") {
        return `#g-card-badge-notebook-revisions-count-page-${pageId}`;
    } else if (selector === "time") {
        return `#g-card-page-${pageId}-update-time`;
    } else if (selector === "view") {
        return `#g-card-action-view-notebook-page-${pageId}`;
    } else if (selector === "edit") {
        return `#g-card-action-edit-notebook-page-${pageId}`;
    }
    throw new Error(`Unknown selector: ${selector}`);
}

describe("PageCard", () => {
    it("displays page title which edits notebook on click", async () => {
        const wrapper = mount(PageCard as object, {
            localVue,
            propsData: { page: FAKE_PAGE_SUMMARY },
            pinia: createTestingPinia({ createSpy: vi.fn }),
        });

        const title = wrapper.find(getSelector("title", FAKE_PAGE_SUMMARY.id));
        expect(title.text()).toBe("My Analysis");
        expect(title.attributes("title")).toBe("Edit Notebook");

        // Click to emit edit event
        await title.trigger("click");
        expect(wrapper.emitted().edit).toBeTruthy();
    });

    it("shows 'Untitled Notebook' when title is empty", () => {
        const wrapper = mount(PageCard as object, {
            localVue,
            propsData: { page: FAKE_PAGE_UNTITLED },
            pinia: createTestingPinia({ createSpy: vi.fn }),
        });

        const title = wrapper.find(getSelector("title", FAKE_PAGE_UNTITLED.id));
        expect(title.text()).toBe("Untitled Notebook");
    });

    it("displays update time badge and revision count", () => {
        const wrapper = mount(PageCard as object, {
            localVue,
            propsData: { page: FAKE_PAGE_SUMMARY },
            pinia: createTestingPinia({ createSpy: vi.fn }),
        });

        expect(wrapper.find(getSelector("time", FAKE_PAGE_SUMMARY.id)).exists()).toBe(true);

        const revisionBadge = wrapper.find(getSelector("revision", FAKE_PAGE_SUMMARY.id));
        expect(revisionBadge.exists()).toBe(true);
        expect(revisionBadge.text()).toBe(
            `${FAKE_PAGE_SUMMARY.revision_ids.length} Revision${FAKE_PAGE_SUMMARY.revision_ids.length !== 1 ? "s" : ""}`,
        );
    });

    it("emits 'view' and 'select' operations correctly", async () => {
        const wrapper = mount(PageCard as object, {
            localVue,
            propsData: { page: FAKE_PAGE_SUMMARY },
            pinia: createTestingPinia({ createSpy: vi.fn }),
        });

        const viewButton = wrapper.find(getSelector("view", FAKE_PAGE_SUMMARY.id));
        await viewButton.trigger("click");
        expect(wrapper.emitted().view).toBeTruthy();

        const editButton = wrapper.find(getSelector("edit", FAKE_PAGE_SUMMARY.id));
        await editButton.trigger("click");
        expect(wrapper.emitted().edit).toBeTruthy();
    });
});
