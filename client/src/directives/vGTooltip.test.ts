import { advanceToJustBeforeTooltipHoverDelay, advanceTooltipHoverDelay } from "@tests/vitest/tooltipTestUtils";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { DirectiveBinding, RendererNode, VNode } from "vue";

import { DEFAULT_TOOLTIP_HOVER_DELAY_MS } from "@/utils/tooltipTiming";

import { vGTooltip } from "./vGTooltip";

import GDropdown from "@/components/BaseComponents/GDropdown.vue";
import GDropdownItem from "@/components/BaseComponents/GDropdownItem.vue";

// The directive hooks never read their vnode arguments.
const unusedVNode = undefined as unknown as VNode<RendererNode, HTMLElement>;

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

        vGTooltip.mounted?.(element, binding, unusedVNode, null);

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

        vGTooltip.unmounted?.(element, bindingForCleanup(), unusedVNode, null);
    });

    test("cancels delayed show when hover leaves early", async () => {
        const element = createTooltipTarget();

        element.dispatchEvent(new Event("mouseenter"));
        await advanceTooltipHoverDelay(100);
        element.dispatchEvent(new Event("mouseleave"));
        await advanceTooltipHoverDelay(500);

        expect(getRenderedTooltip()).toBeNull();

        vGTooltip.unmounted?.(element, bindingForCleanup(), unusedVNode, null);
    });

    test("suppresses native title during delayed hover and restores it on leave", async () => {
        const element = createTooltipTarget("Native title");

        element.dispatchEvent(new Event("mouseenter"));
        expect(element.getAttribute("title")).toBe("");

        await advanceTooltipHoverDelay(100);
        element.dispatchEvent(new Event("mouseleave"));

        expect(element.getAttribute("title")).toBe("Native title");

        vGTooltip.unmounted?.(element, bindingForCleanup(), unusedVNode, null);
    });

    test("shows immediately on focusin", () => {
        const element = createTooltipTarget();

        element.dispatchEvent(new Event("focusin"));
        expect(getRenderedTooltip()).not.toBeNull();

        vGTooltip.unmounted?.(element, bindingForCleanup(), unusedVNode, null);
    });

    test("stays visible when a plain button is clicked", () => {
        const element = createTooltipTarget();

        element.dispatchEvent(new Event("focusin"));
        element.dispatchEvent(new Event("click"));
        expect(getRenderedTooltip()).not.toBeNull();

        vGTooltip.unmounted?.(element, bindingForCleanup(), unusedVNode, null);
    });

    describe("with a controlled show value", () => {
        function mountControlled(show: boolean) {
            return mount(
                {
                    directives: { "g-tooltip": vGTooltip },
                    data: () => ({ show }),
                    template: `<div v-g-tooltip="{ title: 'Cannot connect', show }" />`,
                } as object,
                { attachTo: document.body },
            );
        }

        test("shows and hides when the value changes, without waiting for hover", async () => {
            const wrapper = mountControlled(false);
            expect(getRenderedTooltip()).toBeNull();

            await wrapper.setData({ show: true });
            expect(getRenderedTooltip()?.textContent).toContain("Cannot connect");

            await wrapper.setData({ show: false });
            expect(getRenderedTooltip()).toBeNull();

            wrapper.unmount();
        });

        test("is shown right away when mounted with show set", () => {
            const wrapper = mountControlled(true);
            expect(getRenderedTooltip()).not.toBeNull();
            wrapper.unmount();
        });

        test("leaves a hover-shown tooltip alone on unrelated re-renders", async () => {
            const wrapper = mountControlled(false);
            wrapper.element.dispatchEvent(new Event("mouseenter"));
            await advanceTooltipHoverDelay(DEFAULT_TOOLTIP_HOVER_DELAY_MS);
            expect(getRenderedTooltip()).not.toBeNull();

            await wrapper.setData({ show: false });
            wrapper.vm.$forceUpdate();
            await wrapper.vm.$nextTick();
            expect(getRenderedTooltip()).not.toBeNull();

            wrapper.unmount();
        });
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

            vGTooltip.mounted?.(host, bindingForCleanup(), unusedVNode, null);

            return { host, toggle };
        }

        test("hides when the toggle is clicked", () => {
            const { host, toggle } = createMenuTooltipTarget();

            toggle.dispatchEvent(new Event("focusin", { bubbles: true }));
            expect(getRenderedTooltip()).not.toBeNull();

            toggle.dispatchEvent(new Event("click", { bubbles: true }));
            expect(getRenderedTooltip()).toBeNull();

            vGTooltip.unmounted?.(host, bindingForCleanup(), unusedVNode, null);
        });

        function mountDropdown(template: string) {
            return mount(
                {
                    components: { GDropdown, GDropdownItem },
                    directives: { "g-tooltip": vGTooltip },
                    template,
                } as object,
                { attachTo: document.body },
            );
        }

        test("hides when the toggle of a GDropdown is clicked", async () => {
            const wrapper = mountDropdown(
                `<GDropdown v-g-tooltip title="More options" text="Menu"><GDropdownItem>One</GDropdownItem></GDropdown>`,
            );
            wrapper.element.dispatchEvent(new Event("mouseenter"));
            await advanceTooltipHoverDelay(DEFAULT_TOOLTIP_HOVER_DELAY_MS);
            expect(getRenderedTooltip()).not.toBeNull();

            await wrapper.get(".dropdown-toggle").trigger("click");
            expect(getRenderedTooltip()).toBeNull();

            wrapper.get(".dropdown-item").element.dispatchEvent(new Event("focusin", { bubbles: true }));
            expect(getRenderedTooltip()).toBeNull();

            wrapper.unmount();
        });

        test("names an icon-only toggle instead of the element", async () => {
            const wrapper = mountDropdown(
                `<GDropdown v-g-tooltip title="More options"><template v-slot:button-content><svg /></template></GDropdown>`,
            );
            const toggle = wrapper.get(".dropdown-toggle");

            expect(toggle.attributes("aria-label")).toBe("More options");
            expect(wrapper.attributes("aria-label")).toBeUndefined();

            // The name has to survive GDropdown's own re-renders
            await toggle.trigger("click");
            expect(toggle.attributes("aria-expanded")).toBe("true");
            expect(toggle.attributes("aria-label")).toBe("More options");

            vGTooltip.unmounted?.(wrapper.element as HTMLElement, bindingForCleanup(), unusedVNode, null);
            expect(toggle.attributes("aria-label")).toBeUndefined();
            wrapper.unmount();
        });

        test("keeps the name of a toggle with text or its own label", () => {
            const wrapper = mountDropdown(`<div>
                <GDropdown v-g-tooltip id="text" title="More options" text="Menu" />
                <GDropdown v-g-tooltip id="labelled" title="Upload examples" aria-label="Upload" />
            </div>`);

            expect(wrapper.get("#text .dropdown-toggle").attributes("aria-label")).toBeUndefined();
            expect(wrapper.get("#labelled .dropdown-toggle").attributes("aria-label")).toBe("Upload");
            wrapper.unmount();
        });

        test("does not show while the menu is open", async () => {
            const { host, toggle } = createMenuTooltipTarget();
            toggle.setAttribute("aria-expanded", "true");

            host.dispatchEvent(new Event("mouseenter"));
            await advanceTooltipHoverDelay();
            expect(getRenderedTooltip()).toBeNull();

            toggle.dispatchEvent(new Event("focusin", { bubbles: true }));
            expect(getRenderedTooltip()).toBeNull();

            vGTooltip.unmounted?.(host, bindingForCleanup(), unusedVNode, null);
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
