import { advanceToJustBeforeTooltipHoverDelay, advanceTooltipHoverDelay } from "@tests/vitest/tooltipTestUtils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { DirectiveBinding, VNode } from "vue";

import { vGTooltip } from "./vGTooltip";

describe("vGTooltip", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.runOnlyPendingTimers();
        vi.useRealTimers();
        vi.clearAllMocks();
        document.body.innerHTML = "";
    });

    function createTooltipTarget(title = "Tooltip text") {
        const element = document.createElement("button");
        element.setAttribute("title", title);
        document.body.appendChild(element);

        const binding = {
            modifiers: { hover: true },
            value: undefined,
            arg: undefined,
        } as unknown as DirectiveBinding<unknown>;

        vGTooltip.inserted?.(element, binding, undefined as unknown as VNode, undefined as unknown as VNode);

        return element;
    }

    function getRenderedTooltip() {
        return document.body.querySelector(".g-tooltip-d");
    }

    test("shows on hover after delay", async () => {
        const element = createTooltipTarget();

        element.dispatchEvent(new Event("mouseenter"));
        expect(getRenderedTooltip()).toBeNull();

        advanceToJustBeforeTooltipHoverDelay();
        expect(getRenderedTooltip()).toBeNull();

        await advanceTooltipHoverDelay();
        expect(getRenderedTooltip()).not.toBeNull();

        vGTooltip.unbind?.(element, bindingForCleanup(), undefined as unknown as VNode, undefined as unknown as VNode);
    });

    test("cancels delayed show when hover leaves early", async () => {
        const element = createTooltipTarget();

        element.dispatchEvent(new Event("mouseenter"));
        await advanceTooltipHoverDelay(100);
        element.dispatchEvent(new Event("mouseleave"));
        await advanceTooltipHoverDelay(500);

        expect(getRenderedTooltip()).toBeNull();

        vGTooltip.unbind?.(element, bindingForCleanup(), undefined as unknown as VNode, undefined as unknown as VNode);
    });

    test("suppresses native title during delayed hover and restores it on leave", async () => {
        const element = createTooltipTarget("Native title");

        element.dispatchEvent(new Event("mouseenter"));
        expect(element.getAttribute("title")).toBe("");

        await advanceTooltipHoverDelay(100);
        element.dispatchEvent(new Event("mouseleave"));

        expect(element.getAttribute("title")).toBe("Native title");

        vGTooltip.unbind?.(element, bindingForCleanup(), undefined as unknown as VNode, undefined as unknown as VNode);
    });

    test("shows immediately on focusin", () => {
        const element = createTooltipTarget();

        element.dispatchEvent(new Event("focusin"));
        expect(getRenderedTooltip()).not.toBeNull();

        vGTooltip.unbind?.(element, bindingForCleanup(), undefined as unknown as VNode, undefined as unknown as VNode);
    });
});

function bindingForCleanup() {
    return {
        modifiers: { hover: true },
        value: undefined,
        arg: undefined,
    } as unknown as DirectiveBinding<unknown>;
}
