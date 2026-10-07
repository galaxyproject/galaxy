import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type ComponentPublicInstance, nextTick } from "vue";

import ChangesIndicator from "./ChangesIndicator.vue";

const localVue = getLocalVue();

const SELECTORS = {
    SAVED: "[data-description='item saved indicator']",
    UNSAVED: "[data-description='item unsaved indicator']",
} as const;

type ChangesIndicatorInstance = ComponentPublicInstance & {
    flashSavedIndicator: () => Promise<void>;
};

function mountIndicator(hasChanges = false): VueWrapper<ChangesIndicatorInstance> {
    return mount(ChangesIndicator as object, {
        localVue,
        propsData: { hasChanges },
        // happy-dom only resolves getComputedStyle() (what isVisible() reads) for
        // elements attached to the document, so mount into the body.
        attachTo: document.body,
    }) as unknown as VueWrapper<ChangesIndicatorInstance>;
}

describe("ChangesIndicator", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("renders unsaved changes in a live status region", () => {
        const wrapper = mountIndicator(true);

        expect(wrapper.attributes("role")).toBe("status");
        expect(wrapper.attributes("aria-live")).toBe("polite");
        expect(wrapper.attributes("aria-atomic")).toBe("true");
        expect(wrapper.find(SELECTORS.UNSAVED).text()).toBe("Unsaved");
        expect(wrapper.find(SELECTORS.SAVED).exists()).toBe(false);
    });

    it("shows the saved indicator for 1.5 seconds", async () => {
        const wrapper = mountIndicator();

        await wrapper.vm.flashSavedIndicator();
        expect(wrapper.find(SELECTORS.SAVED).isVisible()).toBe(true);

        vi.advanceTimersByTime(1500);
        await nextTick();

        expect(wrapper.find(SELECTORS.SAVED).isVisible()).toBe(false);
    });

    it("dismisses saved feedback when new changes arrive", async () => {
        const wrapper = mountIndicator();

        await wrapper.vm.flashSavedIndicator();
        await wrapper.setProps({ hasChanges: true });

        expect(wrapper.find(SELECTORS.UNSAVED).isVisible()).toBe(true);
        expect(wrapper.find(SELECTORS.SAVED).exists()).toBe(false);
        expect(vi.getTimerCount()).toBe(0);
    });

    it("does not schedule saved feedback after unmount", async () => {
        const wrapper = mountIndicator();

        const flashPromise = wrapper.vm.flashSavedIndicator();
        wrapper.unmount();
        await flashPromise;

        expect(vi.getTimerCount()).toBe(0);
    });
});
