import { mount, type Wrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";
import { nextTick } from "vue";

import { DEFAULT_TOOLTIP_HOVER_DELAY_MS, INTERACTIVE_POPOVER_CLOSE_DELAY_MS } from "@/utils/tooltipTiming";

import GPopover from "./GPopover.vue";

// happy-dom gives every element a zero-sized rect, so whatever placement floating-ui would
// really resolve to here is meaningless. Pin it and assert on what the component does with it.
const resolved = vi.hoisted(() => ({ placement: "bottom" }));

vi.mock("@floating-ui/dom", () => ({
    computePosition: () =>
        Promise.resolve({
            x: 0,
            y: 0,
            placement: resolved.placement,
            middlewareData: { arrow: { x: 8 } },
        }),
    autoUpdate: (_reference: unknown, _floating: unknown, update: () => void) => {
        update();
        return () => {};
    },
    arrow: () => ({ name: "arrow", fn: () => ({}) }),
    flip: () => ({ name: "flip", fn: () => ({}) }),
    offset: () => ({ name: "offset", fn: () => ({}) }),
    shift: () => ({ name: "shift", fn: () => ({}) }),
}));

let wrapper: Wrapper<Vue> | undefined;

// Queried off the document rather than the wrapper subtree so these stay valid whichever
// container the popover ends up rendering into.
function popoverEl() {
    const el = document.body.querySelector(".popover");
    if (!el) {
        throw new Error("popover element not found");
    }
    return el;
}

async function showPopover(placement: string, resolvedPlacement: string) {
    resolved.placement = resolvedPlacement;

    const target = document.createElement("button");
    target.id = "trigger";
    document.body.appendChild(target);

    wrapper = mount(GPopover as object, {
        attachTo: document.body,
        propsData: { target: "trigger", placement, show: false },
        slots: { default: "body content" },
    });

    // Positioning only kicks in when `show` transitions, so toggle rather than mounting shown.
    await wrapper.setProps({ show: true });

    // The arrow offset is the only signal that computePosition has actually resolved; the
    // placement class already holds a default before then.
    await vi.waitFor(() => {
        if (!popoverEl().querySelector(".arrow")?.getAttribute("style")?.includes("left")) {
            throw new Error("popover not positioned yet");
        }
    });
}

describe("GPopover", () => {
    afterEach(() => {
        wrapper?.destroy();
        wrapper = undefined;
        document.body.innerHTML = "";
    });

    it.each([
        ["bottomleft", "bottom-start", "bs-popover-bottom"],
        ["topleft", "top-start", "bs-popover-top"],
        ["rightbottom", "right-end", "bs-popover-right"],
        ["bottom", "bottom", "bs-popover-bottom"],
        ["right", "right", "bs-popover-right"],
    ])("placement %s resolving to %s gets the %s arrow class", async (placement, resolvedPlacement, expectedClass) => {
        await showPopover(placement, resolvedPlacement);

        // Bootstrap only defines arrow styling for the four base sides, so an aligned
        // placement still has to map onto its base side or the arrow renders untriangled.
        expect([...popoverEl().classList]).toContain(expectedClass);
    });

    it("does not emit an aligned placement class Bootstrap has no rule for", async () => {
        await showPopover("bottomleft", "bottom-start");

        expect([...popoverEl().classList]).not.toContain("bs-popover-bottom-start");
    });

    it("positions the arrow along the popover edge", async () => {
        await showPopover("bottom", "bottom");

        expect(popoverEl().querySelector(".arrow")?.getAttribute("style")).toContain("left: 8px");
    });

    it("relocates the popover to the document body", async () => {
        await showPopover("bottom", "bottom");

        // Being a direct child of body is what keeps it clear of ancestor clipping.
        expect(popoverEl().parentElement).toBe(document.body);
    });

    it("stays inside the dialog that holds its target", async () => {
        const dialog = document.createElement("dialog");
        document.body.appendChild(dialog);
        const target = document.createElement("button");
        target.id = "dialog-trigger";
        dialog.appendChild(target);
        // attachTo replaces the element it is given, so mount onto a stand-in inside the dialog.
        const mountPoint = document.createElement("div");
        dialog.appendChild(mountPoint);

        wrapper = mount(GPopover as object, {
            attachTo: mountPoint,
            propsData: { target: "dialog-trigger", show: false },
            slots: { default: "body content" },
        });
        await wrapper.setProps({ show: true });

        // A modal dialog renders in the top layer and makes everything outside it inert, so a
        // popover appended to the body would be hidden behind it and unusable.
        expect(popoverEl().parentElement).toBe(dialog);
    });

    it("removes the relocated popover when unmounted", async () => {
        await showPopover("bottom", "bottom");

        wrapper?.destroy();
        wrapper = undefined;

        expect(document.body.querySelector(".popover")).toBeNull();
    });
});

// Mounts next to a trigger element and waits for GPopover's deferred listener setup.
async function mountWithTrigger(propsData: Record<string, unknown>) {
    const target = document.createElement("button");
    target.id = "interactive-trigger";
    const mountPoint = document.createElement("div");
    document.body.append(target, mountPoint);

    wrapper = mount(GPopover as object, {
        attachTo: mountPoint,
        propsData: { target: "interactive-trigger", ...propsData },
        slots: { default: "<a href='#'>popover link</a>" },
    });
    await nextTick();
    await nextTick();

    return target;
}

function isShown() {
    return (popoverEl() as HTMLElement).style.display !== "none";
}

async function advance(ms: number) {
    vi.advanceTimersByTime(ms);
    await nextTick();
}

describe("GPopover hover", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        wrapper?.destroy();
        wrapper = undefined;
        document.body.innerHTML = "";
        vi.useRealTimers();
    });

    async function openByHover() {
        const target = await mountWithTrigger({ triggers: "hover" });
        target.dispatchEvent(new MouseEvent("mouseenter"));
        await advance(DEFAULT_TOOLTIP_HOVER_DELAY_MS);
        return target;
    }

    it("does not reopen from a pending hover once the parent closed it", async () => {
        const target = await mountWithTrigger({ triggers: "hover", show: false });

        target.dispatchEvent(new MouseEvent("mouseenter"));
        await advance(DEFAULT_TOOLTIP_HOVER_DELAY_MS / 3);
        await wrapper!.setProps({ show: true });
        await wrapper!.setProps({ show: false });
        await advance(DEFAULT_TOOLTIP_HOVER_DELAY_MS);

        expect(isShown()).toBe(false);
        expect(wrapper!.emitted("update:show")).toBeUndefined();
    });

    it("opens after the shared hover delay", async () => {
        const target = await mountWithTrigger({ triggers: "hover" });

        target.dispatchEvent(new MouseEvent("mouseenter"));
        await advance(DEFAULT_TOOLTIP_HOVER_DELAY_MS - 1);
        expect(isShown()).toBe(false);

        await advance(1);
        expect(isShown()).toBe(true);
    });

    it("does not open when the pointer passes over the trigger", async () => {
        const target = await mountWithTrigger({ triggers: "hover" });

        target.dispatchEvent(new MouseEvent("mouseenter"));
        await advance(DEFAULT_TOOLTIP_HOVER_DELAY_MS / 2);
        target.dispatchEvent(new MouseEvent("mouseleave"));
        await advance(DEFAULT_TOOLTIP_HOVER_DELAY_MS * 2);

        expect(isShown()).toBe(false);
    });

    it("stays open while the pointer moves from the trigger onto the popover", async () => {
        const target = await openByHover();

        target.dispatchEvent(new MouseEvent("mouseleave"));
        await advance(INTERACTIVE_POPOVER_CLOSE_DELAY_MS / 2);
        popoverEl().dispatchEvent(new MouseEvent("mouseenter"));
        await advance(INTERACTIVE_POPOVER_CLOSE_DELAY_MS * 2);

        expect(isShown()).toBe(true);
    });

    it("stays open when the pointer returns from the popover to the trigger", async () => {
        const target = await openByHover();
        target.dispatchEvent(new MouseEvent("mouseleave"));
        popoverEl().dispatchEvent(new MouseEvent("mouseenter"));

        popoverEl().dispatchEvent(new MouseEvent("mouseleave"));
        target.dispatchEvent(new MouseEvent("mouseenter"));
        await advance(DEFAULT_TOOLTIP_HOVER_DELAY_MS * 2);

        expect(isShown()).toBe(true);
    });

    it("closes once the pointer has left both the trigger and the popover", async () => {
        const target = await openByHover();
        target.dispatchEvent(new MouseEvent("mouseleave"));
        popoverEl().dispatchEvent(new MouseEvent("mouseenter"));

        popoverEl().dispatchEvent(new MouseEvent("mouseleave"));
        await advance(INTERACTIVE_POPOVER_CLOSE_DELAY_MS - 1);
        expect(isShown()).toBe(true);

        await advance(1);
        expect(isShown()).toBe(false);
    });
});
