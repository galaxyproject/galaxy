import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import ActivityItem from "./ActivityItem.vue";

const SELECTORS = {
    ITEM: ".activity-item",
    ICON: "[icon='activity-test-icon']",
    INDICATOR: "[data-description='activity indicator']",
    PROGRESS: ".progress",
    PROGRESS_BAR: ".progress-bar",
};

enableAutoUnmount(afterEach);

function mountActivityItem(props = {}) {
    const localVue = getLocalVue();
    return mount(ActivityItem, {
        props: {
            id: "activity-test-id",
            activityBarId: "activity-bar-test-id",
            icon: "activity-test-icon",
            indicator: 0,
            progressPercentage: 0,
            progressStatus: null,
            title: "activity-test-title",
            to: null,
            tooltip: "activity-test-tooltip",
            ...props,
        },
        global: {
            ...withPlugins(localVue, createTestingPinia({ createSpy: vi.fn })),
            stubs: { ...localVue.stubs, FontAwesomeIcon: true },
        },
    });
}

describe("ActivityItem", () => {
    it("renders its title and icon", () => {
        const item = mountActivityItem().find(SELECTORS.ITEM);

        expect(item.text()).toBe("activity-test-title");
        expect(item.find(SELECTORS.ICON).exists()).toBe(true);
    });

    describe("progress bar", () => {
        it("is hidden without a progress status", () => {
            const wrapper = mountActivityItem();

            expect(wrapper.find(SELECTORS.PROGRESS).exists()).toBe(false);
        });

        it.each([
            { progressStatus: "success", shown: ".bg-success", hidden: ".bg-danger" },
            { progressStatus: "danger", shown: ".bg-danger", hidden: ".bg-success" },
        ])("is styled $shown for a $progressStatus status", ({ progressStatus, shown, hidden }) => {
            const wrapper = mountActivityItem({ progressStatus });

            expect(wrapper.find(SELECTORS.PROGRESS).exists()).toBe(true);
            expect(wrapper.find(shown).exists()).toBe(true);
            expect(wrapper.find(hidden).exists()).toBe(false);
        });

        it("fills to the progress percentage as it changes", async () => {
            const wrapper = mountActivityItem({ progressStatus: "success" });
            const bar = wrapper.find(SELECTORS.PROGRESS_BAR);
            expect(bar.element.style.width).toBe("0%");

            await wrapper.setProps({ progressPercentage: 50 });

            expect(bar.element.style.width).toBe("50%");
        });
    });

    describe("indicator", () => {
        it("is hidden when there is nothing to count", () => {
            const wrapper = mountActivityItem({ indicator: 0 });

            expect(wrapper.find(SELECTORS.INDICATOR).exists()).toBe(false);
        });

        it.each([
            { indicator: 1, shown: "1" },
            { indicator: 1000, shown: "99" },
        ])("shows $shown for a count of $indicator", ({ indicator, shown }) => {
            const badge = mountActivityItem({ indicator }).find(SELECTORS.INDICATOR);

            expect(badge.exists()).toBe(true);
            expect(badge.text()).toBe(shown);
        });
    });
});
