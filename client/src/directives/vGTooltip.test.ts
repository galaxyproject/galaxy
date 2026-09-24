import { advanceToJustBeforeTooltipHoverDelay, advanceTooltipHoverDelay } from "@tests/vitest/tooltipTestUtils";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { DirectiveBinding, VNode } from "vue";

import { DEFAULT_TOOLTIP_HOVER_DELAY_MS } from "@/utils/tooltipTiming";

import { vGTooltip } from "./vGTooltip";

import GDropdown from "@/components/BaseComponents/GDropdown.vue";
import GDropdownItem from "@/components/BaseComponents/GDropdownItem.vue";

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

    test("stays visible when a plain button is clicked", () => {
        const element = createTooltipTarget();

        element.dispatchEvent(new Event("focusin"));
        element.dispatchEvent(new Event("click"));
        expect(getRenderedTooltip()).not.toBeNull();

        vGTooltip.unbind?.(element, bindingForCleanup(), undefined as unknown as VNode, undefined as unknown as VNode);
    });

    describe("on a menu button", () => {
        function createMenuTooltipTarget() {
            const host = document.createElement("div");
            host.setAttribute("title", "More options");
            const toggle = document.createElement("button");
            toggle.setAttribute("aria-haspopup", "menu");
            toggle.setAttribute("aria-expanded", "false");
            host.appendChild(toggle);
            document.body.appendChild(host);

            vGTooltip.inserted?.(
                host,
                bindingForCleanup(),
                undefined as unknown as VNode,
                undefined as unknown as VNode,
            );

            return { host, toggle };
        }

        test("hides when the toggle is clicked", () => {
            const { host, toggle } = createMenuTooltipTarget();

            toggle.dispatchEvent(new Event("focusin", { bubbles: true }));
            expect(getRenderedTooltip()).not.toBeNull();

            toggle.dispatchEvent(new Event("click", { bubbles: true }));
            expect(getRenderedTooltip()).toBeNull();

            vGTooltip.unbind?.(host, bindingForCleanup(), undefined as unknown as VNode, undefined as unknown as VNode);
        });

        test("hides when the toggle of a GDropdown is clicked", async () => {
            const wrapper = mount(
                {
                    components: { GDropdown, GDropdownItem },
                    directives: { "g-tooltip": vGTooltip },
                    template: `<GDropdown v-g-tooltip title="More options" text="Menu"><GDropdownItem>One</GDropdownItem></GDropdown>`,
                } as object,
                { attachTo: document.body },
            );
            wrapper.element.dispatchEvent(new Event("mouseenter"));
            await advanceTooltipHoverDelay(DEFAULT_TOOLTIP_HOVER_DELAY_MS);
            expect(getRenderedTooltip()).not.toBeNull();

            await wrapper.get(".dropdown-toggle").trigger("click");
            expect(getRenderedTooltip()).toBeNull();

            wrapper.get(".dropdown-item").element.dispatchEvent(new Event("focusin", { bubbles: true }));
            expect(getRenderedTooltip()).toBeNull();

            wrapper.destroy();
        });

        test("does not show while the menu is open", async () => {
            const { host, toggle } = createMenuTooltipTarget();
            toggle.setAttribute("aria-expanded", "true");

            host.dispatchEvent(new Event("mouseenter"));
            await advanceTooltipHoverDelay();
            expect(getRenderedTooltip()).toBeNull();

            toggle.dispatchEvent(new Event("focusin", { bubbles: true }));
            expect(getRenderedTooltip()).toBeNull();

            vGTooltip.unbind?.(host, bindingForCleanup(), undefined as unknown as VNode, undefined as unknown as VNode);
        });
    });
});

function bindingForCleanup() {
    return {
        modifiers: { hover: true },
        value: undefined,
        arg: undefined,
    } as unknown as DirectiveBinding<unknown>;
}
