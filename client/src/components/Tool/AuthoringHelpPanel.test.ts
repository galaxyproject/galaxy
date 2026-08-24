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

    it("links the parameter index to each parameter section", async () => {
        const wrapper = mount(AuthoringHelpPanel as object);
        const parameterToggle = wrapper.find('[data-description="toggle help section parameters"]');

        await parameterToggle.trigger("click");

        const booleanLink = wrapper.find('a[href="#parameter-boolean"]');
        expect(booleanLink.exists()).toBe(true);
        expect(booleanLink.attributes("target")).toBeUndefined();
        expect(wrapper.find("#parameter-boolean").exists()).toBe(true);
        expect(wrapper.find("#parameter-boolean").classes()).toContain("authoring-help-section-nested");
    });

    it("shows defaults and shell command usage for parameter types", async () => {
        const wrapper = mount(AuthoringHelpPanel as object);
        const booleanToggle = wrapper.find('[data-description="toggle help section parameter-boolean"]');

        await booleanToggle.trigger("click");

        const parameterSection = wrapper.find("#parameter-boolean");
        expect(parameterSection.findAll("th").wrappers.map((header) => header.text())).toEqual([
            "Field",
            "Details",
            "Default",
            "Required",
        ]);
        expect(parameterSection.text()).toContain("Use the parameter in shell_command like this:");
        expect(parameterSection.text()).toContain('include_header="$(inputs.include_header)"');
    });

    it("expands structured fields linked from the tool definition", async () => {
        const wrapper = mount(AuthoringHelpPanel as object);
        const toolDefinitionToggle = wrapper.find('[data-description="toggle help section tool-format"]');

        await toolDefinitionToggle.trigger("click");

        const outputLink = wrapper.find('#tool-format a[href="#outputs"]');
        const outputToggle = wrapper.find('[data-description="toggle help section outputs"]');
        expect(outputLink.exists()).toBe(true);
        expect(outputToggle.attributes("aria-expanded")).toBe("false");

        const clickEvent = new MouseEvent("click", { bubbles: true, cancelable: true });
        outputLink.element.dispatchEvent(clickEvent);
        await wrapper.vm.$nextTick();

        expect(clickEvent.defaultPrevented).toBe(true);
        expect(outputToggle.attributes("aria-expanded")).toBe("true");
        expect(wrapper.find("#outputs .authoring-help-body").exists()).toBe(true);
    });
});
