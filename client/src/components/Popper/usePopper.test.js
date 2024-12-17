import { mount } from "@vue/test-utils";
import { ref, nextTick } from "vue";
import { createPopper } from "@popperjs/core";
import { usePopper } from "./usePopper";

jest.mock("@popperjs/core", () => ({
    createPopper: jest.fn(() => ({
        destroy: jest.fn(),
        update: jest.fn(),
    })),
}));

describe("usePopper", () => {
    let referenceElement;
    let popperElement;

    beforeEach(() => {
        referenceElement = document.createElement("div");
        document.body.appendChild(referenceElement);

        popperElement = document.createElement("div");
        document.body.appendChild(popperElement);
    });

    afterEach(() => {
        document.body.innerHTML = "";
        jest.clearAllMocks();
    });

    const createTestComponent = (trigger = "none") => {
        return mount({
            template: "<div></div>",
            setup() {
                const reference = ref(referenceElement);
                const popper = ref(popperElement);
                const options = { placement: "bottom", trigger };
                const { visible, instance } = usePopper(reference, popper, options);
                return { visible, instance };
            },
        });
    };

    test("should initialize Popper instance on mount", () => {
        createTestComponent();
        expect(createPopper).toHaveBeenCalledWith(referenceElement, popperElement, {
            placement: "bottom",
            strategy: "absolute",
        });
    });

    test("should destroy Popper instance on unmount", () => {
        const wrapper = createTestComponent();
        const popperInstance = createPopper.mock.results[0].value;
        wrapper.destroy();
        expect(popperInstance.destroy).toHaveBeenCalled();
    });

    test("should not change visibility for trigger 'none'", async () => {
        const wrapper = createTestComponent("none");
        const { visible } = wrapper.vm;

        expect(visible).toBe(false);

        referenceElement.dispatchEvent(new Event("click"));
        await nextTick();
        expect(visible).toBe(false);
    });
});
