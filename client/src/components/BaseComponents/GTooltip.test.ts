import { mount, type Wrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";
import { nextTick } from "vue";

import GTooltip from "./GTooltip.vue";

const floatingUi = vi.hoisted(() => ({ stopTracking: vi.fn() }));

vi.mock("@floating-ui/dom", () => ({
    computePosition: () =>
        Promise.resolve({ x: 12, y: 34, placement: "bottom", middlewareData: { arrow: { x: 5, y: 0 } } }),
    autoUpdate: (_reference: unknown, _floating: unknown, update: () => void) => {
        update();
        return floatingUi.stopTracking;
    },
    arrow: () => ({ name: "arrow", fn: () => ({}) }),
    flip: () => ({ name: "flip", fn: () => ({}) }),
    offset: () => ({ name: "offset", fn: () => ({}) }),
    shift: () => ({ name: "shift", fn: () => ({}) }),
}));

let wrapper: Wrapper<Vue> | undefined;

async function showTooltip() {
    const reference = document.createElement("button");
    document.body.appendChild(reference);
    wrapper = mount(GTooltip as object, { attachTo: document.body, propsData: { reference, text: "Hint" } });
    await nextTick();

    reference.dispatchEvent(new FocusEvent("focus"));
    await vi.waitFor(() => expect(wrapper!.attributes("style")).toContain("translate(12px, 34px)"));
    return reference;
}

describe("GTooltip", () => {
    afterEach(() => {
        wrapper?.destroy();
        wrapper = undefined;
        document.body.innerHTML = "";
        floatingUi.stopTracking.mockClear();
    });

    it("positions itself and its arrow once shown", async () => {
        await showTooltip();

        expect(wrapper!.classes()).not.toContain("sr-only");
        expect(wrapper!.find(".g-tooltip-arrow").attributes("style")).toContain("translate(5px, 0px)");
    });

    it("stops tracking its reference when hidden", async () => {
        const reference = await showTooltip();

        reference.dispatchEvent(new FocusEvent("blur"));
        await nextTick();
        await nextTick();

        expect(wrapper!.classes()).toContain("sr-only");
        expect(floatingUi.stopTracking).toHaveBeenCalled();
    });

    it("stops tracking its reference when unmounted while shown", async () => {
        await showTooltip();

        wrapper!.destroy();
        wrapper = undefined;

        expect(floatingUi.stopTracking).toHaveBeenCalled();
    });
});
