import { mount } from "@vue/test-utils";
import PopperComponent from "./Popper.vue";
import { createPopper } from "@popperjs/core";

jest.mock("@popperjs/core", () => ({
    createPopper: jest.fn(() => ({
        destroy: jest.fn(),
        update: jest.fn(),
    })),
}));

function mountTarget(trigger = "click") {
    return mount(PopperComponent, {
        propsData: {
            title: "Test Title",
            placement: "bottom",
            trigger: trigger,
        },
        slots: {
            reference: "<button>Reference</button>",
            default: "<p>Popper Content</p>",
        },
    });
}

describe("PopperComponent.vue", () => {
    afterEach(() => {
        jest.clearAllMocks();
    });

    test("renders component with default props", async () => {
        const wrapper = mountTarget();
        expect(wrapper.find(".popper-element").exists()).toBe(true);
        expect(wrapper.find(".popper-element").isVisible()).toBe(false);
        const reference = wrapper.find("button");
        await reference.trigger("click");
        expect(wrapper.find(".popper-header").exists()).toBe(true);
        expect(wrapper.find(".popper-header").text()).toContain("Test Title");
    });

    test("opens and closes popper on click trigger", async () => {
        const wrapper = mountTarget();
        const reference = wrapper.find("button");
        expect(wrapper.find(".popper-element").isVisible()).toBe(false);
        await reference.trigger("click");
        expect(wrapper.find(".popper-element").isVisible()).toBe(true);
        await wrapper.find(".popper-close").trigger("click");
        expect(wrapper.find(".popper-element").isVisible()).toBe(false);
    });

    test("disables popper when `disabled` prop is true", async () => {
        const wrapper = mountTarget();
        await wrapper.setProps({ disabled: true });
        const reference = wrapper.find("button");
        await reference.trigger("click");
        expect(wrapper.find(".popper-element").isVisible()).toBe(false);
    });

    test("renders the arrow when `arrow` prop is true", () => {
        const wrapper = mountTarget();
        expect(wrapper.find(".popper-arrow").exists()).toBe(true);
    });

    test("does not render the arrow when `arrow` prop is false", async () => {
        const wrapper = mountTarget();
        await wrapper.setProps({ arrow: false });
        expect(wrapper.find(".popper-arrow").exists()).toBe(false);
    });

    test("applies correct mode class", async () => {
        const wrapper = mountTarget();
        await wrapper.setProps({ mode: "light" });
        expect(wrapper.find(".popper-element").classes()).toContain("popper-element-light");
        await wrapper.setProps({ mode: "dark" });
        expect(wrapper.find(".popper-element").classes()).toContain("popper-element-dark");
    });

    test("uses correct placement prop", () => {
        mountTarget();
        expect(createPopper).toHaveBeenCalledWith(
            expect.anything(),
            expect.anything(),
            expect.objectContaining({ placement: "bottom" })
        );
    });

    test("updates visibility when props or watchers change", async () => {
        const wrapper = mountTarget();
        await wrapper.setProps({ disabled: false });
        const reference = wrapper.find("button");
        await reference.trigger("click");
        expect(wrapper.find(".popper-element").isVisible()).toBe(true);
        await wrapper.setProps({ disabled: true });
        expect(wrapper.find(".popper-element").isVisible()).toBe(false);
    });

    test("shows and hides popper on hover trigger", async () => {
        const wrapper = mountTarget("hover");
        const reference = wrapper.find("button");
        const popperElement = wrapper.find(".popper-element");
        expect(popperElement.isVisible()).toBe(false);
        await reference.trigger("mouseover");
        expect(popperElement.isVisible()).toBe(true);
        await reference.trigger("mouseout");
        expect(popperElement.isVisible()).toBe(false);
    });

    test("popper remains visible when clicked inside of popper", async () => {
        const wrapper = mountTarget("click");
        const reference = wrapper.find("button");
        const popperElement = wrapper.find(".popper-element");
        expect(popperElement.isVisible()).toBe(false);
        await reference.trigger("click");
        expect(popperElement.isVisible()).toBe(true);
        await popperElement.trigger("mouseover");
        expect(popperElement.isVisible()).toBe(true);
        await popperElement.trigger("mouseout");
        expect(popperElement.isVisible()).toBe(true);
        await popperElement.trigger("click");
        expect(popperElement.isVisible()).toBe(true);
    });
});
