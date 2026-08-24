import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import AuthoringHelpPanel from "./AuthoringHelpPanel.vue";

describe("AuthoringHelpPanel", () => {
    it("expands and collapses a help section", async () => {
        const wrapper = mount(AuthoringHelpPanel as object);
        const firstToggle = wrapper.find('[data-description^="toggle help section"]');

        expect(wrapper.text()).toContain("Reference");
        expect(wrapper.text()).toContain("Common questions");

        expect(firstToggle.attributes("aria-expanded")).toBe("false");
        expect(wrapper.find(".authoring-help-body").exists()).toBe(false);

        await firstToggle.trigger("click");

        expect(firstToggle.attributes("aria-expanded")).toBe("true");
        expect(wrapper.find(".authoring-help-body").exists()).toBe(true);
        expect(wrapper.find("code.hljs.language-yaml").exists()).toBe(true);
        expect(wrapper.find("code .hljs-attr").exists()).toBe(true);
        expect(wrapper.findAll("th").wrappers.map((header) => header.text())).toEqual(["Field", "Details", "Required"]);

        await firstToggle.trigger("click");

        expect(firstToggle.attributes("aria-expanded")).toBe("false");
        expect(wrapper.find(".authoring-help-body").exists()).toBe(false);
    });
});
