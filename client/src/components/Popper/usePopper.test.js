import { createPopper } from "@popperjs/core";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, test, vi } from "vitest";
import { nextTick, ref } from "vue";

import { usePopper } from "./usePopper";

vi.mock("@popperjs/core", () => ({
    createPopper: vi.fn(() => ({
        destroy: vi.fn(),
        update: vi.fn(),
    })),
}));

function attachedElement() {
    const element = document.createElement("div");
    document.body.appendChild(element);
    return element;
}

/** Mount a component that calls `usePopper` on two elements attached to the document. */
function mountUsePopper(trigger = "none") {
    const reference = attachedElement();
    const popper = attachedElement();
    const wrapper = mount({
        template: "<div></div>",
        setup() {
            return usePopper(ref(reference), ref(popper), { placement: "bottom", trigger });
        },
    });
    return { wrapper, reference, popper };
}

describe("usePopper", () => {
    afterEach(() => {
        document.body.innerHTML = "";
        vi.clearAllMocks();
    });

    test("creates an absolutely positioned, offset Popper instance on mount", () => {
        const { reference, popper } = mountUsePopper();

        expect(createPopper).toHaveBeenCalledWith(reference, popper, {
            placement: "bottom",
            modifiers: [{ name: "offset", options: { offset: [0, 5] } }],
            strategy: "absolute",
        });
    });

    test("destroys the Popper instance on unmount", () => {
        const { wrapper } = mountUsePopper();
        const popperInstance = vi.mocked(createPopper).mock.results[0].value;

        wrapper.unmount();

        expect(popperInstance.destroy).toHaveBeenCalled();
    });

    test("stays hidden when the reference is clicked with trigger 'none'", async () => {
        const { wrapper, reference } = mountUsePopper("none");
        expect(wrapper.vm.visible).toBe(false);

        reference.dispatchEvent(new Event("click"));
        await nextTick();

        expect(wrapper.vm.visible).toBe(false);
    });
});
