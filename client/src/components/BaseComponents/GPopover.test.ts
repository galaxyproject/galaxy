import { mount, type Wrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";
import { nextTick } from "vue";

import { DEFAULT_TOOLTIP_HOVER_DELAY_MS, INTERACTIVE_POPOVER_CLOSE_DELAY_MS } from "@/utils/tooltipTiming";

import GPopover from "./GPopover.vue";

// happy-dom rects are all zero-sized, so pin the resolved placement instead of computing it.
const resolved = vi.hoisted(() => ({
    placement: "bottom",
    middlewareOptions: {} as Record<string, unknown>,
}));

vi.mock("@floating-ui/dom", () => ({
    computePosition: (
        _reference: unknown,
        _floating: unknown,
        config: { middleware: Array<{ name: string; options?: unknown }> },
    ) => {
        resolved.middlewareOptions = Object.fromEntries(config.middleware.map(({ name, options }) => [name, options]));
        return Promise.resolve({
            x: 0,
            y: 0,
            placement: resolved.placement,
            middlewareData: { arrow: { x: 8 } },
        });
    },
    autoUpdate: (_reference: unknown, _floating: unknown, update: () => void) => {
        update();
        return () => {};
    },
    arrow: () => ({ name: "arrow", fn: () => ({}) }),
    flip: (options?: unknown) => ({ name: "flip", options, fn: () => ({}) }),
    offset: () => ({ name: "offset", fn: () => ({}) }),
    shift: (options?: unknown) => ({ name: "shift", options, fn: () => ({}) }),
}));

let wrapper: Wrapper<Vue> | undefined;

// Queried off the document, since the popover relocates out of the wrapper.
function popoverEl() {
    const el = document.body.querySelector(".popover");
    if (!el) {
        throw new Error("popover element not found");
    }
    return el;
}

async function showPopover(placement: string, resolvedPlacement: string, propsData: Record<string, unknown> = {}) {
    resolved.placement = resolvedPlacement;

    const target = document.createElement("button");
    target.id = "trigger";
    document.body.appendChild(target);

    wrapper = mount(GPopover as object, {
        attachTo: document.body,
        propsData: { target: "trigger", placement, show: false, ...propsData },
        slots: { default: "body content" },
    });

    // Positioning only kicks in when `show` transitions, so toggle rather than mounting shown.
    await wrapper.setProps({ show: true });

    // The arrow offset is the only sign that computePosition has resolved.
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

        // Bootstrap styles the arrow only for the four base sides.
        expect([...popoverEl().classList]).toContain(expectedClass);
    });

    it("does not emit an aligned placement class Bootstrap has no rule for", async () => {
        await showPopover("bottomleft", "bottom-start");

        expect([...popoverEl().classList]).not.toContain("bs-popover-bottom-start");
    });

    it("keeps window-bounded popovers inside the viewport rather than the trigger's scroll container", async () => {
        await showPopover("topleft", "top-start", { boundary: "window" });

        // altBoundary would check the trigger's clipping ancestors instead of the popover's (the viewport).
        expect(resolved.middlewareOptions.flip).not.toEqual(expect.objectContaining({ altBoundary: true }));
        expect(resolved.middlewareOptions.shift).not.toEqual(expect.objectContaining({ altBoundary: true }));
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

        // Outside a modal dialog the popover would sit below the top layer and be inert.
        expect(popoverEl().parentElement).toBe(dialog);
    });

    it("sets nothing up when unmounted before its deferred setup ran", async () => {
        const target = document.createElement("button");
        target.id = "short-lived-trigger";
        const mountPoint = document.createElement("div");
        document.body.append(target, mountPoint);

        const shortLived = mount(GPopover as object, {
            attachTo: mountPoint,
            propsData: { target: "short-lived-trigger", triggers: "hover" },
        });
        shortLived.destroy();
        await nextTick();
        await nextTick();

        expect(target.hasAttribute("aria-describedby")).toBe(false);
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

    it("still opens on hover when combined with manual, as BPopover did", async () => {
        const target = await mountWithTrigger({ triggers: "manual hover", show: false });

        target.dispatchEvent(new MouseEvent("mouseenter"));
        await advance(DEFAULT_TOOLTIP_HOVER_DELAY_MS);

        expect(wrapper!.emitted("update:show")).toEqual([[true]]);
    });

    it("ignores hovering a manual-only popover", async () => {
        const target = await mountWithTrigger({ triggers: "manual" });

        target.dispatchEvent(new MouseEvent("mouseenter"));
        await advance(DEFAULT_TOOLTIP_HOVER_DELAY_MS);

        expect(isShown()).toBe(false);
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

    // A 24px trigger at the start of a row of buttons, with a wider popover 10px below it.
    function layOut(target: Element) {
        const place = (el: Element, x: number, y: number, width: number, height: number) =>
            vi.spyOn(el, "getBoundingClientRect").mockReturnValue({
                x,
                y,
                width,
                height,
                left: x,
                top: y,
                right: x + width,
                bottom: y + height,
            } as DOMRect);
        place(target, 134, 0, 24, 20);
        place(popoverEl(), 8, 30, 276, 100);
    }

    function pointer(type: string, on: EventTarget, x: number, y: number, pointerType = "mouse") {
        on.dispatchEvent(new PointerEvent(type, { bubbles: true, clientX: x, clientY: y, pointerType }));
    }

    // A browser reports pointerleave before mouseleave.
    function leave(el: Element, x: number, y: number, pointerType = "mouse") {
        pointer("pointerleave", el, x, y, pointerType);
        el.dispatchEvent(new MouseEvent("mouseleave"));
    }

    it("stays open while the pointer crosses from the trigger towards the popover", async () => {
        const target = await openByHover();
        layOut(target);

        leave(target, 158.5, 12);
        for (const [x, y] of [
            [162, 16],
            [168, 22],
            [175, 28],
        ] as const) {
            pointer("pointermove", document, x, y);
            await advance(INTERACTIVE_POPOVER_CLOSE_DELAY_MS * 2);
        }
        popoverEl().dispatchEvent(new MouseEvent("mouseenter"));
        await advance(INTERACTIVE_POPOVER_CLOSE_DELAY_MS * 2);

        expect(isShown()).toBe(true);
    });

    it("closes once the pointer moves along the trigger's row instead", async () => {
        const target = await openByHover();
        layOut(target);

        leave(target, 158.5, 10);
        pointer("pointermove", document, 162, 10);
        await advance(INTERACTIVE_POPOVER_CLOSE_DELAY_MS * 2);
        expect(isShown()).toBe(true);

        pointer("pointermove", document, 185, 10);
        await advance(INTERACTIVE_POPOVER_CLOSE_DELAY_MS);
        expect(isShown()).toBe(false);
    });

    it("leaves the controls beside the trigger free to click", async () => {
        const target = await openByHover();
        layOut(target);
        const neighbour = document.createElement("button");
        const onClick = vi.fn();
        neighbour.addEventListener("click", onClick);
        document.body.appendChild(neighbour);

        leave(target, 158.5, 10);
        pointer("pointermove", document, 162, 10);
        pointer("pointerdown", neighbour, 162, 10);
        neighbour.click();
        await advance(INTERACTIVE_POPOVER_CLOSE_DELAY_MS);

        // The popover renders only its own parts, so nothing covers the page next to the trigger.
        expect([...popoverEl().children].map((child) => child.className)).toEqual(["arrow", "popover-body"]);
        expect(onClick).toHaveBeenCalledOnce();
        expect(isShown()).toBe(false);
    });

    it.each([
        ["edge", 146, -0.5],
        ["half of a side edge", 158.5, 4],
    ])("closes after the usual delay when the pointer leaves through the trigger's far %s", async (_side, x, y) => {
        const target = await openByHover();
        layOut(target);

        leave(target, x, y);
        await advance(INTERACTIVE_POPOVER_CLOSE_DELAY_MS);

        expect(isShown()).toBe(false);
    });

    it("stays open across the gap on the way back to the trigger", async () => {
        const target = await openByHover();
        layOut(target);
        leave(target, 146, 20.5);
        popoverEl().dispatchEvent(new MouseEvent("mouseenter"));

        leave(popoverEl(), 146, 29.5);
        pointer("pointermove", document, 146, 25);
        await advance(INTERACTIVE_POPOVER_CLOSE_DELAY_MS * 2);
        target.dispatchEvent(new MouseEvent("mouseenter"));
        await advance(INTERACTIVE_POPOVER_CLOSE_DELAY_MS * 2);

        expect(isShown()).toBe(true);
    });

    // How long GPopover waits on a crossing pointer that stopped moving.
    const HOVER_BRIDGE_REST_MS = 300;

    it("closes once the pointer rests short of the popover", async () => {
        const target = await openByHover();
        layOut(target);

        leave(target, 158.5, 12);
        await advance(HOVER_BRIDGE_REST_MS / 2);
        // Each move inside the area restarts the wait.
        pointer("pointermove", document, 162, 16);
        await advance(HOVER_BRIDGE_REST_MS + INTERACTIVE_POPOVER_CLOSE_DELAY_MS - 1);
        expect(isShown()).toBe(true);

        await advance(1);
        expect(isShown()).toBe(false);
    });

    it("stays open when the pointer rests over the popover", async () => {
        const target = await openByHover();
        layOut(target);
        vi.spyOn(popoverEl(), "matches").mockImplementation((selector) => selector === ":hover");

        leave(target, 158.5, 12);
        await advance(HOVER_BRIDGE_REST_MS + INTERACTIVE_POPOVER_CLOSE_DELAY_MS);

        expect(isShown()).toBe(true);
    });

    function appendToBody<T extends Element>(el: T) {
        document.body.appendChild(el);
        return el;
    }

    it.each<[string, string, () => void]>([
        [
            "the pointer leaves the window",
            "mouse",
            () => document.body.dispatchEvent(new PointerEvent("pointerout", { bubbles: true, relatedTarget: null })),
        ],
        [
            "the pointer enters an iframe",
            "mouse",
            () => {
                const frame = appendToBody(document.createElement("iframe"));
                document.body.dispatchEvent(new PointerEvent("pointerout", { bubbles: true, relatedTarget: frame }));
            },
        ],
        [
            "a pen leaves range",
            "pen",
            () =>
                document.body.dispatchEvent(
                    new PointerEvent("pointerleave", { pointerType: "pen", relatedTarget: null }),
                ),
        ],
        ["the pointer is cancelled", "pen", () => pointer("pointercancel", document.body, 162, 16, "pen")],
        [
            "an element scrolls",
            "mouse",
            () => appendToBody(document.createElement("div")).dispatchEvent(new Event("scroll")),
        ],
        ["the wheel turns", "mouse", () => document.body.dispatchEvent(new WheelEvent("wheel", { bubbles: true }))],
    ])("closes after the usual delay when %s mid-crossing", async (_event, pointerType, dispatch) => {
        const target = await openByHover();
        layOut(target);

        leave(target, 158.5, 12, pointerType);
        dispatch();
        await advance(INTERACTIVE_POPOVER_CLOSE_DELAY_MS);

        expect(isShown()).toBe(false);
    });

    it("keeps crossing while the pointer passes between elements in the area", async () => {
        const target = await openByHover();
        layOut(target);
        const passed = appendToBody(document.createElement("div"));

        leave(target, 158.5, 12);
        passed.dispatchEvent(new PointerEvent("pointerout", { bubbles: true, relatedTarget: document.body }));
        passed.dispatchEvent(new PointerEvent("pointerleave", { relatedTarget: document.body }));
        pointer("pointermove", document, 162, 16);
        await advance(INTERACTIVE_POPOVER_CLOSE_DELAY_MS * 2);

        expect(isShown()).toBe(true);
    });

    it("drops a crossing's listeners and timers when unmounted mid-way", async () => {
        const target = await mountWithTrigger({ triggers: "hover", show: true });
        layOut(target);
        const added = vi.spyOn(document, "addEventListener");
        const removed = vi.spyOn(document, "removeEventListener");

        leave(target, 158.5, 12);
        const unmounted = wrapper!;
        unmounted.destroy();
        wrapper = undefined;

        expect(added).toHaveBeenCalled();
        for (const [type, handler] of added.mock.calls) {
            expect(removed).toHaveBeenCalledWith(type, handler, true);
        }
        expect(vi.getTimerCount()).toBe(0);
        pointer("pointermove", document, 400, 400);
        await advance(HOVER_BRIDGE_REST_MS + INTERACTIVE_POPOVER_CLOSE_DELAY_MS);
        expect(unmounted.emitted("update:show")).toBeUndefined();

        added.mockRestore();
        removed.mockRestore();
    });

    it("does not hold the popover open for touch", async () => {
        const target = await openByHover();
        layOut(target);

        leave(target, 162, 16, "touch");
        await advance(INTERACTIVE_POPOVER_CLOSE_DELAY_MS);

        expect(isShown()).toBe(false);
    });

    it("keeps a pending open when the target is re-passed as a new function for the same element", async () => {
        const target = await mountWithTrigger({ triggers: "hover" });

        target.dispatchEvent(new MouseEvent("mouseenter"));
        await advance(DEFAULT_TOOLTIP_HOVER_DELAY_MS / 2);
        await wrapper!.setProps({ target: () => target });
        await advance(DEFAULT_TOOLTIP_HOVER_DELAY_MS / 2);

        expect(isShown()).toBe(true);
    });

    it("moves its listeners to a new target element", async () => {
        const oldTarget = await mountWithTrigger({ triggers: "hover" });
        const newTarget = document.createElement("button");
        document.body.appendChild(newTarget);

        await wrapper!.setProps({ target: newTarget });
        await nextTick();
        oldTarget.dispatchEvent(new MouseEvent("mouseenter"));
        await advance(DEFAULT_TOOLTIP_HOVER_DELAY_MS);
        expect(isShown()).toBe(false);

        newTarget.dispatchEvent(new MouseEvent("mouseenter"));
        await advance(DEFAULT_TOOLTIP_HOVER_DELAY_MS);
        expect(isShown()).toBe(true);
        expect(oldTarget.hasAttribute("aria-describedby")).toBe(false);
        expect(newTarget.getAttribute("aria-describedby")).toBe(popoverEl().id);
    });

    it("announces a popover that was mounted open", async () => {
        await mountWithTrigger({ triggers: "hover", show: true });
        await nextTick();

        expect(wrapper!.emitted("shown")).toHaveLength(1);
    });

    it("reports hover opens and closes through show.sync", async () => {
        const target = await mountWithTrigger({ triggers: "hover", show: false });

        target.dispatchEvent(new MouseEvent("mouseenter"));
        await advance(DEFAULT_TOOLTIP_HOVER_DELAY_MS);
        await wrapper!.setProps({ show: true });
        target.dispatchEvent(new MouseEvent("mouseleave"));
        await advance(INTERACTIVE_POPOVER_CLOSE_DELAY_MS);

        expect(wrapper!.emitted("update:show")).toEqual([[true], [false]]);
    });

    it.each([
        ["open", false],
        ["close", true],
    ])("drops a pending %s when unmounted", async (_pending, show) => {
        const target = await mountWithTrigger({ triggers: "hover", show });
        target.dispatchEvent(new MouseEvent(show ? "mouseleave" : "mouseenter"));

        const unmounted = wrapper!;
        unmounted.destroy();
        wrapper = undefined;
        await advance(DEFAULT_TOOLTIP_HOVER_DELAY_MS);

        expect(unmounted.emitted("update:show")).toBeUndefined();
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

describe("GPopover description", () => {
    afterEach(() => {
        wrapper?.destroy();
        wrapper = undefined;
        document.body.innerHTML = "";
    });

    it("describes its hover trigger with the popover", async () => {
        const target = await mountWithTrigger({ triggers: "hover" });

        expect(popoverEl().getAttribute("role")).toBe("tooltip");
        expect(target.getAttribute("aria-describedby")).toBe(popoverEl().id);
    });

    it.each([
        ["an element", (element: HTMLElement) => element],
        ["a getter", (element: HTMLElement) => () => element],
    ])("anchors to %s", async (_kind, toTarget) => {
        const target = document.createElement("button");
        const mountPoint = document.createElement("div");
        document.body.append(target, mountPoint);

        wrapper = mount(GPopover as object, {
            attachTo: mountPoint,
            propsData: { target: toTarget(target), triggers: "hover" },
        });
        await nextTick();
        await nextTick();

        expect(target.getAttribute("aria-describedby")).toBe(popoverEl().id);
    });

    it("keeps existing descriptions and restores them when unmounted", async () => {
        const target = document.createElement("button");
        target.id = "described-trigger";
        target.setAttribute("aria-describedby", "existing-hint");
        const mountPoint = document.createElement("div");
        document.body.append(target, mountPoint);

        wrapper = mount(GPopover as object, {
            attachTo: mountPoint,
            propsData: { target: "described-trigger", triggers: "hover focus" },
        });
        await nextTick();
        await nextTick();

        expect(target.getAttribute("aria-describedby")).toBe(`existing-hint ${popoverEl().id}`);

        wrapper.destroy();
        wrapper = undefined;

        expect(target.getAttribute("aria-describedby")).toBe("existing-hint");
    });
});

describe("GPopover click", () => {
    afterEach(() => {
        wrapper?.destroy();
        wrapper = undefined;
        document.body.innerHTML = "";
    });

    async function openByClick() {
        const target = await mountWithTrigger({ triggers: "click blur", title: "Person" });
        target.click();
        await nextTick();
        return target;
    }

    it("closes on a click outside the trigger and popover", async () => {
        await openByClick();
        const outside = document.createElement("div");
        document.body.appendChild(outside);

        outside.click();
        await nextTick();

        expect(isShown()).toBe(false);
    });

    it("closes when the trigger is clicked again", async () => {
        const target = await openByClick();
        expect(isShown()).toBe(true);

        target.click();
        await nextTick();

        expect(isShown()).toBe(false);
    });
});
