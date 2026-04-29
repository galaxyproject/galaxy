import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";

import type { PageRevisionSummary } from "@/api/pages";

import PageRevisionList from "./PageRevisionList.vue";

const localVue = getLocalVue();

function makeRevision(overrides: Partial<PageRevisionSummary> = {}): PageRevisionSummary {
    return {
        id: "rev-1",
        page_id: "page-1",
        edit_source: "user",
        create_time: "2025-06-15T10:30:00Z",
        update_time: "2025-06-15T12:45:00Z",
        ...overrides,
    };
}

const SELECTORS = {
    LOADING: "[data-description='sidebar list loading']",
    EMPTY: "[data-description='sidebar list empty']",
    REVISION_ITEMS: ".sidebar-items",
    REVISION_ITEM: "[data-description='revision item']",
    RESTORE_BUTTON: "[data-description='restore revision button']",
    CURRENT_BADGE: ".badge-primary",
};

interface MountOptions {
    revisions?: PageRevisionSummary[];
    isLoading?: boolean;
    isReverting?: boolean;
}

function mountComponent(options: MountOptions = {}) {
    const { revisions = [], isLoading = false, isReverting = false } = options;
    return mount(PageRevisionList as object, {
        localVue,
        propsData: { revisions, isLoading, isReverting },
        stubs: { FontAwesomeIcon: true },
    });
}

describe("PageRevisionList", () => {
    describe("Loading state", () => {
        it("shows loading spinner and text when isLoading is true", () => {
            const wrapper = mountComponent({ isLoading: true });

            const loading = wrapper.find(SELECTORS.LOADING);
            expect(loading.exists()).toBe(true);
            expect(loading.text()).toContain("Loading revisions");
        });

        it("does not show revision items when loading", () => {
            const wrapper = mountComponent({ isLoading: true });

            expect(wrapper.find(SELECTORS.REVISION_ITEMS).exists()).toBe(false);
        });
    });

    describe("Empty state", () => {
        it("shows 'No revisions found.' when revisions is empty and not loading", () => {
            const wrapper = mountComponent({ revisions: [] });

            const empty = wrapper.find(SELECTORS.EMPTY);
            expect(empty.exists()).toBe(true);
            expect(empty.text()).toBe("No revisions found.");
        });

        it("does not show revision items when empty", () => {
            const wrapper = mountComponent({ revisions: [] });

            expect(wrapper.find(SELECTORS.REVISION_ITEMS).exists()).toBe(false);
        });
    });

    describe("Rendering revision items", () => {
        let wrapper: Wrapper<Vue>;
        const revisions = [
            makeRevision({ id: "rev-current", edit_source: "user", create_time: "2025-06-16T14:00:00Z" }),
            makeRevision({ id: "rev-older", edit_source: "agent", create_time: "2025-06-15T10:30:00Z" }),
            makeRevision({ id: "rev-oldest", edit_source: "restore", create_time: "2025-06-14T08:00:00Z" }),
        ];

        beforeEach(() => {
            wrapper = mountComponent({ revisions });
        });

        it("renders one row per revision", () => {
            const items = wrapper.findAll(SELECTORS.REVISION_ITEM);
            expect(items.length).toBe(3);
        });

        it("shows 'Current' badge only on the first (index 0) item", () => {
            const items = wrapper.findAll(SELECTORS.REVISION_ITEM);
            expect(items.at(0).find(SELECTORS.CURRENT_BADGE).exists()).toBe(true);
            expect(items.at(1).find(SELECTORS.CURRENT_BADGE).exists()).toBe(false);
            expect(items.at(2).find(SELECTORS.CURRENT_BADGE).exists()).toBe(false);
        });

        it("shows correct edit_source labels: user->Manual, agent->AI, restore->Restored", () => {
            const items = wrapper.findAll(SELECTORS.REVISION_ITEM);
            expect(items.at(0).text()).toContain("Manual");
            expect(items.at(1).text()).toContain("AI");
            expect(items.at(2).text()).toContain("Restored");
        });

        it("shows formatted dates", () => {
            const items = wrapper.findAll(SELECTORS.REVISION_ITEM);
            for (let i = 0; i < items.length; i++) {
                const text = items.at(i).text();
                expect(text).toMatch(/\w{3}\s+\d/);
            }
        });

        it("shows 'Unknown' label when edit_source is null", () => {
            const wrapper = mountComponent({
                revisions: [makeRevision({ edit_source: null })],
            });

            expect(wrapper.find(SELECTORS.REVISION_ITEM).text()).toContain("Unknown");
        });
    });

    describe("Restore button visibility", () => {
        it("does NOT show restore button on index 0 (current revision)", () => {
            const wrapper = mountComponent({
                revisions: [makeRevision({ id: "rev-current" }), makeRevision({ id: "rev-older" })],
            });

            const items = wrapper.findAll(SELECTORS.REVISION_ITEM);
            expect(items.at(0).find(SELECTORS.RESTORE_BUTTON).exists()).toBe(false);
        });

        it("shows restore button on non-current revisions (index > 0)", () => {
            const wrapper = mountComponent({
                revisions: [makeRevision({ id: "rev-current" }), makeRevision({ id: "rev-older" })],
            });

            const items = wrapper.findAll(SELECTORS.REVISION_ITEM);
            expect(items.at(1).find(SELECTORS.RESTORE_BUTTON).exists()).toBe(true);
            expect(items.at(1).find(SELECTORS.RESTORE_BUTTON).text()).toContain("Restore");
        });
    });

    describe("Events", () => {
        it("emits 'select' with revision id when row is clicked", async () => {
            const wrapper = mountComponent({
                revisions: [makeRevision({ id: "rev-1" }), makeRevision({ id: "rev-2" })],
            });

            const items = wrapper.findAll(SELECTORS.REVISION_ITEM);
            await items.at(1).trigger("click");

            expect(wrapper.emitted().select).toBeTruthy();
            expect(wrapper.emitted().select![0]![0]).toBe("rev-2");
        });

        it("emits 'restore' with revision id when restore button is clicked", async () => {
            const wrapper = mountComponent({
                revisions: [makeRevision({ id: "rev-current" }), makeRevision({ id: "rev-older" })],
            });

            const restoreBtn = wrapper.findAll(SELECTORS.RESTORE_BUTTON).at(0);
            await restoreBtn.trigger("click");

            expect(wrapper.emitted().restore).toBeTruthy();
            expect(wrapper.emitted().restore![0]![0]).toBe("rev-older");
        });

        it("restore button click does not also emit 'select' (click.stop)", async () => {
            const wrapper = mountComponent({
                revisions: [makeRevision({ id: "rev-current" }), makeRevision({ id: "rev-older" })],
            });

            const restoreBtn = wrapper.findAll(SELECTORS.RESTORE_BUTTON).at(0);
            await restoreBtn.trigger("click");

            expect(wrapper.emitted().restore).toBeTruthy();
            expect(wrapper.emitted().select).toBeFalsy();
        });
    });

    describe("isReverting prop", () => {
        it("disables restore buttons when isReverting is true", () => {
            const wrapper = mountComponent({
                revisions: [makeRevision({ id: "rev-current" }), makeRevision({ id: "rev-older" })],
                isReverting: true,
            });

            const restoreBtn = wrapper.find(SELECTORS.RESTORE_BUTTON);
            expect(restoreBtn.attributes("disabled")).toBeTruthy();
        });

        it("restore buttons are enabled when isReverting is false", () => {
            const wrapper = mountComponent({
                revisions: [makeRevision({ id: "rev-current" }), makeRevision({ id: "rev-older" })],
                isReverting: false,
            });

            const restoreBtn = wrapper.find(SELECTORS.RESTORE_BUTTON);
            expect(restoreBtn.attributes("disabled")).toBeUndefined();
        });
    });
});
