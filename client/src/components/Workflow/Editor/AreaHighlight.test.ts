import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AreaHighlight from "./AreaHighlight.vue";

const localVue = getLocalVue();

describe("AreaHighlight", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("starts without the blink class", () => {
        const wrapper = mount(AreaHighlight as object, { localVue });
        expect(wrapper.classes()).not.toContain("blink");
    });

    it("adds blink class 100ms after show() and removes it after 1100ms total", async () => {
        const wrapper = mount(AreaHighlight as object, { localVue });
        const bounds = { x: 10, y: 20, width: 100, height: 50 };

        const vm = wrapper.vm as unknown as InstanceType<typeof AreaHighlight>;
        vm.show(bounds);

        // Not yet blinking — waiting for the 100ms delay
        expect(wrapper.classes()).not.toContain("blink");

        // After 100ms the blink class appears
        await vi.advanceTimersByTimeAsync(100);
        expect(wrapper.classes()).toContain("blink");

        // After the 1000ms animation the blink class is removed
        await vi.advanceTimersByTimeAsync(1000);
        expect(wrapper.classes()).not.toContain("blink");
    });

    it("positions the element based on bounds passed to show()", async () => {
        const wrapper = mount(AreaHighlight as object, { localVue });
        const bounds = { x: 15, y: 30, width: 200, height: 80 };

        const vm = wrapper.vm as unknown as InstanceType<typeof AreaHighlight>;
        vm.show(bounds);

        await vi.advanceTimersByTimeAsync(100);

        const style = wrapper.attributes("style");
        expect(style).toContain("left: 15px");
        expect(style).toContain("top: 30px");
        expect(style).toContain("width: 200px");
        expect(style).toContain("height: 80px");
    });

    it("resets blink before restarting when show() is called again", async () => {
        const wrapper = mount(AreaHighlight as object, { localVue });
        const vm = wrapper.vm as unknown as InstanceType<typeof AreaHighlight>;
        const bounds = { x: 0, y: 0, width: 50, height: 50 };

        vm.show(bounds);
        await vi.advanceTimersByTimeAsync(100);
        expect(wrapper.classes()).toContain("blink");

        // Calling show again resets blink immediately
        vm.show(bounds);
        await wrapper.vm.$nextTick();
        expect(wrapper.classes()).not.toContain("blink");
    });
});
