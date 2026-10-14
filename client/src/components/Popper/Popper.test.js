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
import { nextTick } from "vue";

import { DEFAULT_TOOLTIP_HOVER_DELAY_MS, INTERACTIVE_POPOVER_CLOSE_DELAY_MS } from "@/utils/tooltipTiming";

import * as PopperStories from "./Popper.stories";

import PopperComponent from "./Popper.vue";

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

    test("omits the header and close control without a title", async () => {
        const wrapper = mountPlainPopper();
        await wrapper.setProps({ title: undefined });
        await wrapper.get("button").trigger("click");
        expect(wrapper.get(".popper-element").isVisible()).toBe(true);
        expect(wrapper.find(".popper-header").exists()).toBe(false);
        expect(wrapper.find(".popper-close").exists()).toBe(false);
    });

    test("offers a named native close button and returns focus to its trigger", async () => {
        const wrapper = mountPopper();
        await wrapper.get("button").trigger("click");
        const close = wrapper.get(".popper-close");
        expect(close.element).toHaveAccessibleName("Close");
        expect(close.element.tagName).toBe("BUTTON");
        expect(close.attributes("type")).toBe("button");
        close.element.focus();
        expect(document.activeElement).toBe(close.element);
        await close.trigger("click");
        expect(wrapper.get(".popper-element").isVisible()).toBe(false);
        expect(document.activeElement).toBe(wrapper.get("button").element);
    });

    test("returns focus to the trigger when Escape dismisses the focused popup", async () => {
        const wrapper = mountPopper();
        await wrapper.get("button").trigger("click");
        const close = wrapper.get(".popper-close");
        close.element.focus();
        expect(document.activeElement).toBe(close.element);
        await close.trigger("keydown", { key: "Escape" });
        expect(wrapper.get(".popper-element").isVisible()).toBe(false);
        expect(document.activeElement).toBe(wrapper.get("button").element);
    });

    test("closes a hover popup on Escape only when focus is inside it", async () => {
        const wrapper = mountPopper("hover", true);
        const reference = wrapper.get("button");
        const popperElement = wrapper.get(".popper-element");
        await reference.trigger("mouseover");
        await advanceTooltipHoverDelay(DEFAULT_TOOLTIP_HOVER_DELAY_MS);
        expect(popperElement.isVisible()).toBe(true);

        reference.element.focus();
        await reference.trigger("keydown", { key: "Escape" });
        expect(popperElement.isVisible()).toBe(true);

        const close = wrapper.get(".popper-close");
        close.element.focus();
        await close.trigger("keydown", { key: "Escape" });
        expect(popperElement.isVisible()).toBe(false);
        expect(document.activeElement).toBe(reference.element);
    });

    test("returns focus to an external reference without stealing focus from elsewhere", async () => {
        const reference = document.createElement("button");
        reference.textContent = "Open details";
        const elsewhere = document.createElement("button");
        elsewhere.textContent = "Other action";
        container.append(reference, elsewhere);
        const wrapper = mount(PopperComponent, {
            props: { title: "Details", referenceEl: reference, trigger: "click" },
            attachTo: container,
        });

        reference.click();
        await nextTick();
        const close = wrapper.get(".popper-close");
        expect(close.element).toHaveAccessibleName("Close");
        close.element.focus();
        expect(document.activeElement).toBe(close.element);
        await close.trigger("click");
        expect(wrapper.get(".popper-element").isVisible()).toBe(false);
        expect(document.activeElement).toBe(reference);

        reference.click();
        await nextTick();
        expect(wrapper.get(".popper-element").isVisible()).toBe(true);
        elsewhere.focus();
        await close.trigger("click");
        expect(wrapper.get(".popper-element").isVisible()).toBe(false);
        expect(document.activeElement).toBe(elsewhere);
    });

    test("keeps a hover popup open on Escape when its reference cannot take focus back", async () => {
        const wrapper = mount(PopperComponent, {
            props: { interactive: true },
            slots: {
                reference: "<span>Icon</span>",
                default: '<a href="#more">Read more</a>',
            },
            attachTo: container,
        });
        await wrapper.get(".popper-reference-container").trigger("mouseover");
        await advanceTooltipHoverDelay(DEFAULT_TOOLTIP_HOVER_DELAY_MS);
        const link = wrapper.get("a");
        link.element.focus();
        await link.trigger("keydown", { key: "Escape" });
        expect(wrapper.get(".popper-element").isVisible()).toBe(true);
        expect(document.activeElement).toBe(link.element);
    });

    test("keeps a hover popup open on Escape when its external reference is not focusable", async () => {
        const reference = document.createElement("span");
        container.append(reference);
        const wrapper = mount(PopperComponent, {
            props: { referenceEl: reference, interactive: true },
            slots: { default: '<a href="#more">Read more</a>' },
            attachTo: container,
        });
        reference.dispatchEvent(new MouseEvent("mouseover"));
        await advanceTooltipHoverDelay(DEFAULT_TOOLTIP_HOVER_DELAY_MS);
        const link = wrapper.get("a");
        link.element.focus();
        await link.trigger("keydown", { key: "Escape" });
        expect(wrapper.get(".popper-element").isVisible()).toBe(true);
    });

    test("returns focus to the first enabled, tabbable control in the reference", async () => {
        const wrapper = mount(PopperComponent, {
            props: { title: "Details", trigger: "click" },
            slots: {
                reference:
                    '<span><button disabled>Disabled</button><span tabindex="-1">Skipped</span><button class="target">Open</button></span>',
            },
            attachTo: container,
        });
        await wrapper.get(".target").trigger("click");
        const close = wrapper.get(".popper-close");
        close.element.focus();
        await close.trigger("keydown", { key: "Escape" });
        expect(wrapper.get(".popper-element").isVisible()).toBe(false);
        expect(document.activeElement).toBe(wrapper.get(".target").element);
    });

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
