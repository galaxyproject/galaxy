import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import AuthoringHelpPanel from "./AuthoringHelpPanel.vue";

describe("AuthoringHelpPanel", () => {
    it("expands and collapses a help section", async () => {
        const wrapper = mount(AuthoringHelpPanel as object);
        const quickStartToggle = wrapper.find('[data-description="toggle help section quick-start"]');
        const toolDefinitionToggle = wrapper.find('[data-description="toggle help section tool-format"]');

        expect(wrapper.text()).toContain("Reference");
        expect(wrapper.text()).toContain("Common questions");

        expect(quickStartToggle.attributes("aria-expanded")).toBe("false");
        expect(wrapper.find(".authoring-help-body").exists()).toBe(false);

        await quickStartToggle.trigger("click");

        expect(quickStartToggle.attributes("aria-expanded")).toBe("true");
        expect(wrapper.find(".authoring-help-body").exists()).toBe(true);
        expect(wrapper.find("code.hljs.language-yaml").exists()).toBe(true);
        expect(wrapper.find("code .hljs-attr").exists()).toBe(true);

        await quickStartToggle.trigger("click");

        expect(quickStartToggle.attributes("aria-expanded")).toBe("false");
        expect(wrapper.find(".authoring-help-body").exists()).toBe(false);

        await toolDefinitionToggle.trigger("click");
        expect(wrapper.findAll("th").wrappers.map((header) => header.text())).toEqual(["Field", "Details", "Required"]);
    });

    it("links the parameter index to each parameter section", async () => {
        const wrapper = mount(AuthoringHelpPanel as object);
        const parameterToggle = wrapper.find('[data-description="toggle help section parameters"]');
        const booleanSection = wrapper.find("#parameter-boolean");

        expect(booleanSection.isVisible()).toBe(false);

        await parameterToggle.trigger("click");

        const booleanLink = wrapper.find('a[href="#parameter-boolean"]');
        expect(booleanLink.exists()).toBe(true);
        expect(booleanLink.attributes("target")).toBeUndefined();
        expect(booleanSection.isVisible()).toBe(true);
        expect(booleanSection.classes()).toContain("authoring-help-section-nested");
    });

    it("shows defaults and shell command usage for parameter types", async () => {
        const wrapper = mount(AuthoringHelpPanel as object);
        const parameterToggle = wrapper.find('[data-description="toggle help section parameters"]');
        const booleanToggle = wrapper.find('[data-description="toggle help section parameter-boolean"]');

        await parameterToggle.trigger("click");
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

    it("nests output types under outputs", async () => {
        const wrapper = mount(AuthoringHelpPanel as object);
        const outputToggle = wrapper.find('[data-description="toggle help section outputs"]');
        const dataOutputToggle = wrapper.find('[data-description="toggle help section output-data"]');

        expect(wrapper.find("#output-data").isVisible()).toBe(false);
        await outputToggle.trigger("click");

        expect(wrapper.find('#outputs a[href="#output-data"]').exists()).toBe(true);
        expect(wrapper.find("#output-data").classes()).toContain("authoring-help-section-nested");
        expect(wrapper.find("#output-data").isVisible()).toBe(true);

        await dataOutputToggle.trigger("click");
        expect(wrapper.find("#output-data").text()).toContain("from_work_dir");
        expect(wrapper.find("#output-data").text()).toContain("result.txt");
    });

    it("nests validator types under input parameters", async () => {
        const wrapper = mount(AuthoringHelpPanel as object);
        const parameterToggle = wrapper.find('[data-description="toggle help section parameters"]');
        const validatorsToggle = wrapper.find('[data-description="toggle help section validators"]');
        const regexToggle = wrapper.find('[data-description="toggle help section validator-regex"]');

        expect(wrapper.find("#validators").isVisible()).toBe(false);
        expect(wrapper.find("#validator-regex").isVisible()).toBe(false);

        await parameterToggle.trigger("click");
        expect(wrapper.find("#validators").isVisible()).toBe(true);
        expect(wrapper.find("#validator-regex").isVisible()).toBe(false);

        await validatorsToggle.trigger("click");
        expect(wrapper.find('#validators a[href="#validator-regex"]').exists()).toBe(true);
        expect(wrapper.find("#validator-regex").isVisible()).toBe(true);

        await regexToggle.trigger("click");
        expect(wrapper.find("#validator-regex").text()).toContain("^[ACGT]+$");
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
        expect(wrapper.find("#output-data").isVisible()).toBe(true);
    });

    it("opens a section programmatically for editor hover links", async () => {
        const wrapper = mount(AuthoringHelpPanel as object);
        const outputToggle = wrapper.find('[data-description="toggle help section output-data"]');

        expect(outputToggle.attributes("aria-expanded")).toBe("false");
        expect(
            await (wrapper.vm as unknown as { openSection: (id: string) => Promise<boolean> }).openSection(
                "output-data",
            ),
        ).toBe(true);
        await wrapper.vm.$nextTick();

        expect(outputToggle.attributes("aria-expanded")).toBe("true");
        expect(wrapper.find("#output-data").isVisible()).toBe(true);
    });
});
