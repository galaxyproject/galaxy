import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { mount } from "@vue/test-utils";

import VisualizationHeader from "./VisualizationHeader.vue";

describe("VisualizationHeader.vue", () => {
    const mockPlugin = {
        html: "My Plugin",
        description: "A plugin for testing.",
        logo: "/static/plugin-logo.svg",
    };

    const mountComponent = (pluginOverride = {}) => {
        return mount(VisualizationHeader, {
            propsData: {
                plugin: { ...mockPlugin, ...pluginOverride },
            },
        });
    };

    it("renders fallback icon when logo is not available", () => {
        const wrapper = mountComponent({ logo: undefined });
        const fallbackIcon = wrapper.findComponent(FontAwesomeIcon);
        expect(fallbackIcon.exists()).toBe(true);
        expect(fallbackIcon.classes()).toContain("p-1");
    });

    it("renders plugin HTML inside .plugin-list-title", () => {
        const wrapper = mountComponent();
        const title = wrapper.find(".plugin-list-title");
        expect(title.html()).toContain("My Plugin");
    });

    it("renders plugin logo when available", () => {
        const wrapper = mountComponent();
        const logo = wrapper.find("img[alt='visualization']");
        expect(logo.exists()).toBe(true);
        expect(logo.attributes("src")).toBe("http://localhost/static/plugin-logo.svg");
    });

    it("renders plugin description inside .plugin-list-text", () => {
        const wrapper = mountComponent();
        const description = wrapper.find(".plugin-list-text");
        expect(description.text()).toBe("A plugin for testing.");
    });

    it("renders structure with correct classes", () => {
        const wrapper = mountComponent();
        expect(wrapper.classes()).toContain("d-flex");
        expect(wrapper.find(".plugin-thumbnail").exists()).toBe(true);
    });
});
