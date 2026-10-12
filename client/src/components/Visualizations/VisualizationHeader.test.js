import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import VisualizationHeader from "./VisualizationHeader.vue";

describe("VisualizationHeader.vue", () => {
    enableAutoUnmount(afterEach);

    /** @type {import("@/api/plugins").Plugin} */
    const plugin = {
        name: "test-plugin",
        href: "/plugins/test-plugin",
        html: "My Plugin",
        description: "A plugin for testing.",
        logo: "/static/plugin-logo.svg",
    };

    const mountComponent = (pluginOverride = {}) => {
        return mount(VisualizationHeader, {
            props: {
                plugin: { ...plugin, ...pluginOverride },
            },
        });
    };

    it("renders fallback icon when logo is not available", () => {
        const wrapper = mountComponent({ logo: undefined });
        const fallbackIcon = wrapper.getComponent(FontAwesomeIcon);
        expect(fallbackIcon.exists()).toBe(true);
        expect(fallbackIcon.classes()).toContain("p-1");
    });

    it("renders plugin HTML inside .plugin-list-title", () => {
        const wrapper = mountComponent();
        const title = wrapper.get(".plugin-list-title");
        expect(title.html()).toContain("My Plugin");
    });

    it("renders plugin logo when available", () => {
        const wrapper = mountComponent();
        const logo = wrapper.get("img[alt='visualization']");
        expect(logo.exists()).toBe(true);
        expect(logo.attributes("src")).toBe("http://localhost/static/plugin-logo.svg");
    });

    it("renders plugin description inside .plugin-list-text", () => {
        const wrapper = mountComponent();
        const description = wrapper.get(".plugin-list-text");
        expect(description.text()).toBe("A plugin for testing.");
    });

    it("renders structure with correct classes", () => {
        const wrapper = mountComponent();
        expect(wrapper.classes()).toContain("d-flex");
        expect(wrapper.find(".plugin-thumbnail").exists()).toBe(true);
    });
});
