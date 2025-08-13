import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import FormCard from "./FormCard";

const globalConfig = getLocalVue();

describe("FormCard", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(FormCard, {
            props: {
                title: "title",
                description: "description",
                icon: "icon-class",
            },
            global: globalConfig.global,
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
