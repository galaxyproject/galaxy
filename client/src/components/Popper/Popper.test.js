import { createPopper } from "@popperjs/core";
import {
    advanceToJustBeforeTooltipHoverDelay,
    advanceTooltipHoverDelay,
    runPendingTimersAndFlush,
} from "@tests/vitest/tooltipTestUtils";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { DEFAULT_TOOLTIP_HOVER_DELAY_MS, INTERACTIVE_POPOVER_CLOSE_DELAY_MS } from "@/utils/tooltipTiming";

import PopperComponent from "./Popper.vue";

vi.mock("@popperjs/core", () => ({
    createPopper: vi.fn(() => ({
        destroy: vi.fn(),
        update: vi.fn(),
    })),
}));

// happy-dom only resolves getComputedStyle() (what `isVisible()` reads) for
// elements attached to the document, so mount into the body rather than a
// detached container.
let container;

function mountPopper(trigger = "click", interactive = false) {
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
        attachTo: container,
    });
}

describe("PopperComponent.vue", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        container = document.createElement("div");
        document.body.appendChild(container);
    });

    afterEach(() => {
        vi.clearAllTimers();
        vi.useRealTimers();
        vi.clearAllMocks();
        container.remove();
    });
    enableAutoUnmount(afterEach);

    test("renders its configured title when opened", async () => {
        const wrapper = mountPopper();
        expect(wrapper.find(".popper-element").exists()).toBe(true);
        expect(wrapper.get(".popper-element").isVisible()).toBe(false);
        const reference = wrapper.get("button");
        await reference.trigger("click");
        expect(wrapper.find(".popper-header").exists()).toBe(true);
        expect(wrapper.get(".popper-header").text()).toContain("Test Title");
    });

    test("opens and closes popper on click trigger", async () => {
        const wrapper = mountPopper();
        const reference = wrapper.get("button");
        expect(wrapper.get(".popper-element").isVisible()).toBe(false);
        await reference.trigger("click");
        expect(wrapper.get(".popper-element").isVisible()).toBe(true);
        await wrapper.get(".popper-close").trigger("click");
        expect(wrapper.get(".popper-element").isVisible()).toBe(false);
    });

    test("closes a click-triggered popper when the document is clicked outside it", async () => {
        const wrapper = mountPopper();
        await wrapper.get("button").trigger("click");
        expect(wrapper.get(".popper-element").isVisible()).toBe(true);

        document.body.click();
        await wrapper.vm.$nextTick();

        expect(wrapper.get(".popper-element").isVisible()).toBe(false);
    });

    test("disables popper when `disabled` prop is true", async () => {
        const wrapper = mountPopper();
        await wrapper.setProps({ disabled: true });
        const reference = wrapper.get("button");
        await reference.trigger("click");
        expect(wrapper.get(".popper-element").isVisible()).toBe(false);
    });

    test("renders the arrow when `arrow` prop is true", () => {
        const wrapper = mountPopper();
        expect(wrapper.find(".popper-arrow").exists()).toBe(true);
    });

    test("does not render the arrow when `arrow` prop is false", async () => {
        const wrapper = mountPopper();
        await wrapper.setProps({ arrow: false });
        expect(wrapper.find(".popper-arrow").exists()).toBe(false);
    });

    test("applies correct mode class", async () => {
        const wrapper = mountPopper();
        await wrapper.setProps({ mode: "light" });
        expect(wrapper.get(".popper-element").classes()).toContain("popper-element-light");
        await wrapper.setProps({ mode: "dark" });
        expect(wrapper.get(".popper-element").classes()).toContain("popper-element-dark");
    });

    test("uses correct placement prop", () => {
        mountPopper();
        expect(createPopper).toHaveBeenCalledWith(
            expect.anything(),
            expect.anything(),
            expect.objectContaining({ placement: "bottom" }),
        );
    });

    test("updates visibility when props or watchers change", async () => {
        const wrapper = mountPopper();
        await wrapper.setProps({ disabled: false });
        const reference = wrapper.get("button");
        await reference.trigger("click");
        expect(wrapper.get(".popper-element").isVisible()).toBe(true);
        await wrapper.setProps({ disabled: true });
        expect(wrapper.get(".popper-element").isVisible()).toBe(false);
    });

    test("shows and hides popper on hover trigger over reference", async () => {
        const wrapper = mountPopper("hover");
        const reference = wrapper.get("button");
        const popperElement = wrapper.get(".popper-element");
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
        const wrapper = mountPopper("hover", true);
        const reference = wrapper.get("button");
        const popperElement = wrapper.get(".popper-element");
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
        const wrapper = mountPopper("click");
        const reference = wrapper.get("button");
        const popperElement = wrapper.get(".popper-element");
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
