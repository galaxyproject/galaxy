import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import Target from "./CellButton.vue";

const localVue = getLocalVue();

async function mountTarget(props = {}) {
    return mount(Target, {
        localVue,
        propsData: props,
        slots: {
            default: "<div class='button_content' />",
        },
    });
}

describe("CellButton.vue", () => {
    it("should render button", async () => {
        const wrapper = await mountTarget({
            title: "button-title",
        });
        expect(wrapper.find(".button_content").exists()).toBeTruthy();
        expect(wrapper.attributes()["title"]).toBe("button-title");
        expect(wrapper.classes()).not.toContain("active");
        expect(wrapper.classes()).toContain("btn-outline-primary");
        await wrapper.setProps({ active: true });
        expect(wrapper.classes()).toContain("active");
        expect(wrapper.classes()).toContain("btn-outline-secondary");
        await wrapper.trigger("click");
        expect(wrapper.emitted("click")).toBeTruthy();
        expect(wrapper.emitted("click")?.length).toBe(1);
        wrapper.element.blur = jest.fn();
        await wrapper.trigger("mouseleave");
        expect(wrapper.element.blur).toHaveBeenCalled();
    });
});
