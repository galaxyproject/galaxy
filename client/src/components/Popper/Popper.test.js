import { createPopper } from "@popperjs/core";
import {
    advanceToJustBeforeTooltipHoverDelay,
    advanceTooltipHoverDelay,
    runPendingTimersAndFlush,
} from "@tests/vitest/tooltipTestUtils";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { DEFAULT_TOOLTIP_HOVER_DELAY_MS, INTERACTIVE_POPOVER_CLOSE_DELAY_MS } from "@/utils/tooltipTiming";

import PopperComponent from "./Popper.vue";

vi.mock("@popperjs/core", () => ({
    createPopper: vi.fn(() => ({
        destroy: vi.fn(),
        update: vi.fn(),
    })),
}));

function mountTarget(trigger = "click", interactive = false) {
    return mount(PopperComponent, {
        props: {
            title: "Test Title",
            placement: "bottom",
            interactive,
            trigger,
        },
        slots: {
            reference: "<button>Reference</button>",
            default: "<p>Popper Content</p>",
        },
    });
}

describe("PopperComponent.vue", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.runOnlyPendingTimers();
        vi.useRealTimers();
        vi.clearAllMocks();
    });

    test("renders component with default props", async () => {
        const wrapper = mountTarget();
        expect(wrapper.find(".popper-element").exists()).toBe(true);
        expect(wrapper.find(".popper-element").isVisible()).toBe(false);
        const reference = wrapper.find("button");
        await reference.trigger("click");
        expect(wrapper.find(".popper-header").exists()).toBe(true);
        expect(wrapper.find(".popper-header").text()).toContain("Test Title");
    });

    test("opens and closes popper on click trigger", async () => {
        const wrapper = mountTarget();
        const reference = wrapper.find("button");
        expect(wrapper.find(".popper-element").isVisible()).toBe(false);
        await reference.trigger("click");
        expect(wrapper.find(".popper-element").isVisible()).toBe(true);
        await wrapper.find(".popper-close").trigger("click");
        expect(wrapper.find(".popper-element").isVisible()).toBe(false);
    });

    test("disables popper when `disabled` prop is true", async () => {
        const wrapper = mountTarget();
        await wrapper.setProps({ disabled: true });
        const reference = wrapper.find("button");
        await reference.trigger("click");
        expect(wrapper.find(".popper-element").isVisible()).toBe(false);
    });

    test("renders the arrow when `arrow` prop is true", () => {
        const wrapper = mountTarget();
        expect(wrapper.find(".popper-arrow").exists()).toBe(true);
    });

    test("does not render the arrow when `arrow` prop is false", async () => {
        const wrapper = mountTarget();
        await wrapper.setProps({ arrow: false });
        expect(wrapper.find(".popper-arrow").exists()).toBe(false);
    });

    test("applies correct mode class", async () => {
        const wrapper = mountTarget();
        await wrapper.setProps({ mode: "light" });
        expect(wrapper.find(".popper-element").classes()).toContain("popper-element-light");
        await wrapper.setProps({ mode: "dark" });
        expect(wrapper.find(".popper-element").classes()).toContain("popper-element-dark");
    });

    test("uses correct placement prop", () => {
        mountTarget();
        expect(createPopper).toHaveBeenCalledWith(
            expect.anything(),
            expect.anything(),
            expect.objectContaining({ placement: "bottom" }),
        );
    });

    test("updates visibility when props or watchers change", async () => {
        const wrapper = mountTarget();
        await wrapper.setProps({ disabled: false });
        const reference = wrapper.find("button");
        await reference.trigger("click");
        expect(wrapper.find(".popper-element").isVisible()).toBe(true);
        await wrapper.setProps({ disabled: true });
        expect(wrapper.find(".popper-element").isVisible()).toBe(false);
    });

    test("shows and hides popper on hover trigger over reference", async () => {
        const wrapper = mountTarget("hover");
        const reference = wrapper.find("button");
        const popperElement = wrapper.find(".popper-element");
        expect(popperElement.isVisible()).toBe(false);
        await reference.trigger("mouseover");
        expect(popperElement.isVisible()).toBe(false);
        advanceToJustBeforeTooltipHoverDelay();
        expect(popperElement.isVisible()).toBe(false);
        await advanceTooltipHoverDelay();
        expect(popperElement.isVisible()).toBe(true);
        await reference.trigger("mouseout");
        await runPendingTimersAndFlush();
        expect(popperElement.isVisible()).toBe(false);
    });

    test("popper remains visible when hovering over popper", async () => {
        const wrapper = mountTarget("hover", true);
        const reference = wrapper.find("button");
        const popperElement = wrapper.find(".popper-element");
        expect(popperElement.isVisible()).toBe(false);
        await reference.trigger("mouseover");
        await advanceTooltipHoverDelay(DEFAULT_TOOLTIP_HOVER_DELAY_MS);
        expect(popperElement.isVisible()).toBe(true);
        await reference.trigger("mouseout");
        await advanceTooltipHoverDelay(INTERACTIVE_POPOVER_CLOSE_DELAY_MS / 2);
        expect(popperElement.isVisible()).toBe(true);
        await popperElement.trigger("mouseover");
        await advanceTooltipHoverDelay(INTERACTIVE_POPOVER_CLOSE_DELAY_MS * 2);
        await popperElement.trigger("mouseout");
        await advanceTooltipHoverDelay(INTERACTIVE_POPOVER_CLOSE_DELAY_MS * 2);
        expect(popperElement.isVisible()).toBe(false);
    });

    test("popper remains visible when clicked inside of popper", async () => {
        const wrapper = mountTarget("click");
        const reference = wrapper.find("button");
        const popperElement = wrapper.find(".popper-element");
        expect(popperElement.isVisible()).toBe(false);
        await reference.trigger("click");
        expect(popperElement.isVisible()).toBe(true);
        await popperElement.trigger("mouseover");
        expect(popperElement.isVisible()).toBe(true);
        await popperElement.trigger("mouseout");
        expect(popperElement.isVisible()).toBe(true);
        await popperElement.trigger("click");
        expect(popperElement.isVisible()).toBe(true);
    });
});
