import { mount, type Wrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";

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

        // Vue 2.7 has no built-in Teleport, so a bare <Teleport> leaves the popover nested in an
        // unknown element and still subject to ancestor clipping. Being a direct child of body is
        // the whole point of the escape hatch.
        expect(popoverEl().parentElement).toBe(document.body);
    });
});
