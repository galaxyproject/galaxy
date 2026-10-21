import { createPopper } from "@popperjs/core";
import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import {
    advanceToJustBeforeTooltipHoverDelay,
    advanceTooltipHoverDelay,
    runPendingTimersAndFlush,
} from "@tests/vitest/tooltipTestUtils";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { DEFAULT_TOOLTIP_HOVER_DELAY_MS, INTERACTIVE_POPOVER_CLOSE_DELAY_MS } from "@/utils/tooltipTiming";

import * as PopperStories from "./Popper.stories";

const stories = composeStories(PopperStories);

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

function mountPlainPopper() {
    return mount(PopperStories.InputPopover, {
        props: PopperStories.default.args,
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
    const mountStory = useStoryMount();

    function mountPopper(trigger = "click", interactive = false) {
        const story =
            trigger === "click" ? stories.ClickDetails : interactive ? stories.InteractiveHelp : stories.HoverHelp;
        return mountStory(story, { attachTo: container });
    }

    // Initial disabled visibility has no independent positive sync point; keep this guard in unit.
    test("disables popper when `disabled` prop is true", async () => {
        const wrapper = mountPlainPopper();
        await wrapper.setProps({ disabled: true });
        const reference = wrapper.get("button");
        await reference.trigger("click");
        expect(wrapper.get(".popper-element").isVisible()).toBe(false);
    });

    // Decorative arrows, mode variants, and placement options stay as structural/contract checks.
    test("renders the arrow when `arrow` prop is true", () => {
        const wrapper = mountPopper();
        expect(wrapper.find(".popper-arrow").exists()).toBe(true);
    });

    test("does not render the arrow when `arrow` prop is false", async () => {
        const wrapper = mountPlainPopper();
        await wrapper.setProps({ arrow: false });
        expect(wrapper.find(".popper-arrow").exists()).toBe(false);
    });

    test("applies correct mode class", async () => {
        const wrapper = mountPlainPopper();
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

    // Fake-timer boundaries are the contract, including the interactive close grace period.
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
});
