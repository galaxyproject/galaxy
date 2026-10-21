import { advanceToJustBeforeTooltipHoverDelay, advanceTooltipHoverDelay } from "@tests/vitest/tooltipTestUtils";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ref } from "vue";

import { DEFAULT_TOOLTIP_HOVER_DELAY_MS } from "@/utils/tooltipTiming";

import { useAccessibleHover } from "./accessibleHover";

enableAutoUnmount(afterEach);

describe("useAccessibleHover", () => {
    let element: HTMLButtonElement;
    beforeEach(() => {
        vi.useFakeTimers();
        element = document.createElement("button");
        document.body.appendChild(element);
    });

    afterEach(() => {
        vi.clearAllTimers();
        vi.useRealTimers();
        vi.clearAllMocks();
        element.remove();
    });

    function mountWithElement(onEnter?: () => void, onExit?: () => void) {
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

    test("enters on hover only after the tooltip delay", async () => {
        const onEnter = vi.fn();
        mountWithElement(onEnter);

        element.dispatchEvent(new Event("mouseenter"));
        expect(onEnter).not.toHaveBeenCalled();

        advanceToJustBeforeTooltipHoverDelay();
        expect(onEnter).not.toHaveBeenCalled();

        await advanceTooltipHoverDelay();
        expect(onEnter).toHaveBeenCalledTimes(1);
    });

    test("cancels delayed hover enter on mouseleave", async () => {
        const onEnter = vi.fn();
        const onExit = vi.fn();
        mountWithElement(onEnter, onExit);

        element.dispatchEvent(new Event("mouseenter"));
        await advanceTooltipHoverDelay(100);
        element.dispatchEvent(new Event("mouseleave"));
        await advanceTooltipHoverDelay(500);

        expect(onEnter).not.toHaveBeenCalled();
        expect(onExit).not.toHaveBeenCalled();
    });

    test("enters immediately on keyboard focus", () => {
        const onEnter = vi.fn();
        mountWithElement(onEnter);

        element.dispatchEvent(new Event("focus"));
        expect(onEnter).toHaveBeenCalledTimes(1);
    });
});
