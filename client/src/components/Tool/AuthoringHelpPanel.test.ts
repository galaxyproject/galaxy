import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { type DOMWrapper, enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import AuthoringHelpPanel from "./AuthoringHelpPanel.vue";

enableAutoUnmount(afterEach);

type HelpPanelWrapper = ReturnType<typeof mountAuthoringHelpPanel>;
type EditorHelpPanelApi = Pick<InstanceType<typeof AuthoringHelpPanel>, "openSection">;

// happy-dom only resolves getComputedStyle() (what isVisible() reads) for elements
// attached to the document, so mount into the body rather than a detached container.
let container: HTMLDivElement;
let clipboardDescriptor: PropertyDescriptor | undefined;

function mountAuthoringHelpPanel() {
    return mount(AuthoringHelpPanel, {
        global: withPlugins(getLocalVue(), createTestingPinia({ createSpy: vi.fn })),
        attachTo: container,
    });
}

function getSection(wrapper: HelpPanelWrapper, id: string) {
    return wrapper.get(`#${id}`);
}

function getSectionToggle(wrapper: HelpPanelWrapper, id: string) {
    return wrapper.get(`[data-description="toggle help section ${id}"]`);
}

// These links are handled by a native listener on the panel, so dispatch a
// cancelable DOM event to exercise both expansion and prevented navigation.
async function followHelpLink(link: DOMWrapper<Element>) {
    const event = new MouseEvent("click", { bubbles: true, cancelable: true });
    link.element.dispatchEvent(event);
    await nextTick();
    return event;
}

describe("AuthoringHelpPanel", () => {
    beforeEach(() => {
        clipboardDescriptor = Object.getOwnPropertyDescriptor(navigator, "clipboard");
        container = document.createElement("div");
        document.body.appendChild(container);
    });

    afterEach(() => {
        container.remove();
        if (clipboardDescriptor) {
            Object.defineProperty(navigator, "clipboard", clipboardDescriptor);
        } else {
            Reflect.deleteProperty(navigator, "clipboard");
        }
    });

    it("expands and collapses quick start, then renders tool definition reference content", async () => {
        const wrapper = mountAuthoringHelpPanel();
        const quickStartToggle = getSectionToggle(wrapper, "quick-start");
        const toolDefinitionToggle = getSectionToggle(wrapper, "tool-format");

        expect(wrapper.text()).toContain("Reference");
        expect(wrapper.text()).toContain("Common questions");

        expect(quickStartToggle.attributes("aria-expanded")).toBe("false");
        expect(wrapper.find(".authoring-help-body").exists()).toBe(false);

        await quickStartToggle.trigger("click");

        expect(quickStartToggle.attributes("aria-expanded")).toBe("true");
        expect(wrapper.find(".authoring-help-body").exists()).toBe(true);
        expect(wrapper.find("code.hljs.language-yaml").exists()).toBe(true);
        expect(wrapper.find("code .hljs-attr").exists()).toBe(true);
        expect(wrapper.find(".authoring-code-example-label").text()).toBe("Example");

        await quickStartToggle.trigger("click");

        expect(quickStartToggle.attributes("aria-expanded")).toBe("false");
        expect(wrapper.find(".authoring-help-body").exists()).toBe(false);

        await toolDefinitionToggle.trigger("click");
        expect(wrapper.findAll("th").map((header) => header.text())).toEqual(["Field", "Details", "Required"]);
        const containerHelpLink = wrapper.find('#tool-format a[href="/help/terms/galaxy.tools.container"]');
        const commandHelpLink = wrapper.find('#tool-format a[href="/help/terms/unix.commandLine"]');
        expect(containerHelpLink.text()).toBe("container image");
        expect(commandHelpLink.text()).toBe("command line");
        expect(containerHelpLink.attributes("style")).toContain("text-decoration-style: dashed");
    });

    it("copies the displayed quick-start example to the clipboard", async () => {
        const writeText = vi.fn().mockResolvedValue(undefined);
        Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
        const wrapper = mountAuthoringHelpPanel();

        await getSectionToggle(wrapper, "quick-start").trigger("click");
        const expected = wrapper.find(".authoring-code-example code").element.textContent;
        await wrapper.find(".authoring-code-example-copy").trigger("click");

        expect(writeText).toHaveBeenCalledWith(expected);
    });

    it("opens the nested boolean parameter section from its index link", async () => {
        const wrapper = mountAuthoringHelpPanel();
        const parameterToggle = getSectionToggle(wrapper, "parameters");
        const booleanSection = getSection(wrapper, "parameter-boolean");

        expect(booleanSection.isVisible()).toBe(false);

        await parameterToggle.trigger("click");

        const booleanLink = wrapper.find('a[href="#parameter-boolean"]');
        expect(booleanLink.exists()).toBe(true);
        expect(booleanLink.attributes("target")).toBeUndefined();
        expect(booleanSection.isVisible()).toBe(false);

        const clickEvent = await followHelpLink(booleanLink);

        expect(clickEvent.defaultPrevented).toBe(true);
        expect(booleanSection.isVisible()).toBe(true);
        expect(booleanSection.classes()).toContain("authoring-help-section-nested");
    });

    it("shows defaults and shell command usage for parameter types", async () => {
        const wrapper = mountAuthoringHelpPanel();

        const editorHelpPanel: EditorHelpPanelApi = wrapper.vm;
        expect(await editorHelpPanel.openSection("parameter-boolean")).toBe(true);

        const parameterSection = getSection(wrapper, "parameter-boolean");
        expect(parameterSection.findAll("th").map((header) => header.text())).toEqual([
            "Field",
            "Details",
            "Default",
            "Required",
        ]);
        expect(parameterSection.text()).toContain("Use the parameter in shell_command like this:");
        expect(parameterSection.text()).toContain('include_header="$(inputs.include_header)"');
    });

    it("nests output types under outputs", async () => {
        const wrapper = mountAuthoringHelpPanel();
        const outputToggle = getSectionToggle(wrapper, "outputs");
        const dataOutputToggle = getSectionToggle(wrapper, "output-data");
        const dataOutputSection = getSection(wrapper, "output-data");
        const formatSourceSection = getSection(wrapper, "output-data-format-source");

        expect(dataOutputSection.isVisible()).toBe(false);
        expect(formatSourceSection.isVisible()).toBe(false);
        await outputToggle.trigger("click");

        expect(wrapper.find('#outputs a[href="#output-data"]').exists()).toBe(true);
        expect(dataOutputSection.classes()).toContain("authoring-help-section-nested");
        expect(dataOutputSection.isVisible()).toBe(false);

        await getSectionToggle(wrapper, "output-types-reference").trigger("click");
        expect(dataOutputSection.isVisible()).toBe(true);

        await dataOutputToggle.trigger("click");
        expect(dataOutputSection.text()).toContain("from_work_dir");
        expect(dataOutputSection.text()).toContain("result.txt");
        expect(wrapper.find('#output-data a[href="#output-data-format-source"]').exists()).toBe(true);
        expect(formatSourceSection.isVisible()).toBe(true);
        expect(formatSourceSection.attributes("style")).toContain("margin-left: 2rem");

        const formatSourceLink = wrapper.find('#output-data a[href="#output-data-format-source"]');
        const clickEvent = await followHelpLink(formatSourceLink);

        expect(clickEvent.defaultPrevented).toBe(true);
        expect(formatSourceSection.text()).toContain("format_source: reads");
        expect(getSectionToggle(wrapper, "output-data-format-source").attributes("aria-expanded")).toBe("true");
    });

    it("nests validator types under input parameters", async () => {
        const wrapper = mountAuthoringHelpPanel();
        const parameterToggle = getSectionToggle(wrapper, "parameters");
        const validatorsToggle = getSectionToggle(wrapper, "validators");
        const regexToggle = getSectionToggle(wrapper, "validator-regex");
        const validatorsSection = getSection(wrapper, "validators");
        const regexSection = getSection(wrapper, "validator-regex");

        expect(validatorsSection.isVisible()).toBe(false);
        expect(regexSection.isVisible()).toBe(false);

        await parameterToggle.trigger("click");
        expect(validatorsSection.isVisible()).toBe(true);
        expect(regexSection.isVisible()).toBe(false);

        await validatorsToggle.trigger("click");
        expect(wrapper.find('#validators a[href="#validator-regex"]').exists()).toBe(true);
        expect(regexSection.isVisible()).toBe(false);

        await getSectionToggle(wrapper, "validator-types-reference").trigger("click");
        expect(regexSection.isVisible()).toBe(true);

        await regexToggle.trigger("click");
        expect(regexSection.text()).toContain("^[ACGT]+$");
    });

    it("expands structured fields linked from the tool definition", async () => {
        const wrapper = mountAuthoringHelpPanel();
        const toolDefinitionToggle = getSectionToggle(wrapper, "tool-format");

        await toolDefinitionToggle.trigger("click");

        const outputLink = wrapper.find('#tool-format a[href="#outputs"]');
        const outputToggle = getSectionToggle(wrapper, "outputs");
        expect(outputLink.exists()).toBe(true);
        expect(outputToggle.attributes("aria-expanded")).toBe("false");

        const clickEvent = await followHelpLink(outputLink);

        expect(clickEvent.defaultPrevented).toBe(true);
        expect(outputToggle.attributes("aria-expanded")).toBe("true");
        expect(wrapper.find("#outputs .authoring-help-body").exists()).toBe(true);
        expect(getSection(wrapper, "output-data").isVisible()).toBe(false);

        const dataOutputLink = wrapper.find('#outputs a[href="#output-data"]');
        const dataOutputClick = await followHelpLink(dataOutputLink);

        expect(dataOutputClick.defaultPrevented).toBe(true);
        expect(getSection(wrapper, "output-data").isVisible()).toBe(true);
    });

    it("opens a section programmatically for editor hover links", async () => {
        const wrapper = mountAuthoringHelpPanel();
        const outputToggle = getSectionToggle(wrapper, "output-data");

        expect(outputToggle.attributes("aria-expanded")).toBe("false");
        const editorHelpPanel: EditorHelpPanelApi = wrapper.vm;
        expect(await editorHelpPanel.openSection("output-data")).toBe(true);

        expect(outputToggle.attributes("aria-expanded")).toBe("true");
        expect(getSection(wrapper, "output-data").isVisible()).toBe(true);
    });
});
