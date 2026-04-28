import { advanceToJustBeforeTooltipHoverDelay, advanceTooltipHoverDelay } from "@tests/vitest/tooltipTestUtils";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ref } from "vue";

import { DEFAULT_TOOLTIP_HOVER_DELAY_MS } from "@/utils/tooltipTiming";

import { useAccessibleHover } from "./accessibleHover";

describe("useAccessibleHover", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.runOnlyPendingTimers();
        vi.useRealTimers();
        vi.clearAllMocks();
        document.body.innerHTML = "";
    });

    function mountWithElement(element: HTMLElement, onEnter?: () => void, onExit?: () => void) {
        const elementRef = ref<HTMLElement | null>(element);

        return mount({
            template: "<div />",
            setup() {
                useAccessibleHover(() => elementRef.value, onEnter, onExit, {
                    showDelayMs: DEFAULT_TOOLTIP_HOVER_DELAY_MS,
                    delayFocusEnter: false,
                });
            },
        });
    }

    test("delays hover enter", async () => {
        const element = document.createElement("button");
        document.body.appendChild(element);

        const onEnter = vi.fn();
        const wrapper = mountWithElement(element, onEnter);

        element.dispatchEvent(new Event("mouseenter"));
        expect(onEnter).not.toHaveBeenCalled();

        advanceToJustBeforeTooltipHoverDelay();
        expect(onEnter).not.toHaveBeenCalled();

        await advanceTooltipHoverDelay();
        expect(onEnter).toHaveBeenCalledTimes(1);

        wrapper.unmount();
    });

    test("cancels delayed hover enter on mouseleave", async () => {
        const element = document.createElement("button");
        document.body.appendChild(element);

        const onEnter = vi.fn();
        const onExit = vi.fn();
        const wrapper = mountWithElement(element, onEnter, onExit);

        element.dispatchEvent(new Event("mouseenter"));
        await advanceTooltipHoverDelay(100);
        element.dispatchEvent(new Event("mouseleave"));
        await advanceTooltipHoverDelay(500);

        expect(onEnter).not.toHaveBeenCalled();
        expect(onExit).not.toHaveBeenCalled();

        wrapper.unmount();
    });

    test("shows immediately on focus", () => {
        const element = document.createElement("button");
        document.body.appendChild(element);

        const onEnter = vi.fn();
        const wrapper = mountWithElement(element, onEnter);

        element.dispatchEvent(new Event("focus"));
        expect(onEnter).toHaveBeenCalledTimes(1);

        wrapper.unmount();
    });
});
