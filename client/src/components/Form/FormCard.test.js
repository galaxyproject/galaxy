import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import FormCard from "./FormCard";

const localVue = getLocalVue();

describe("FormCard", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(FormCard, {
            propsData: {
                title: "title",
                description: "description",
                icon: "icon-class",
            },
            localVue,
        });
    });

    it("check props", async () => {
        const title = wrapper.find(".portlet-title-text");
        expect(title.text()).toBe("title");
        const description = wrapper.find(".portlet-title-description");
        expect(description.text()).toBe("description");
        const icon = wrapper.find(".portlet-title-icon");
        expect(icon.classes()).toContain("icon-class");
    });
});
