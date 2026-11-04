import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type VueWrapper } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { WorkflowInputSection } from "@/components/Workflow/Run/inputSections";

import FormInputSection from "./FormInputSection.vue";
import FormElement from "@/components/Form/FormElement.vue";

const localVue = getLocalVue();

const SECTIONS: WorkflowInputSection[] = [
    { name: "advanced", label: "Advanced options", expanded: false },
    { name: "references", expanded: true },
];

function mountForm(section?: string, inputSections: WorkflowInputSection[] = SECTIONS) {
    return shallowMount(FormInputSection as any, {
        localVue,
        propsData: {
            step: { id: 3, type: "parameter_input", section },
            inputSections,
        },
    });
}

function element(wrapper: VueWrapper, id: string) {
    return wrapper.findAllComponents(FormElement).find((e) => e.attributes("id") === id)!;
}

function selectOptions(wrapper: VueWrapper): { label: string; value: string }[] {
    return element(wrapper, "__input_section").props("attributes")!.data as { label: string; value: string }[];
}

describe("FormInputSection", () => {
    it("offers no section, the defined sections and a new one", () => {
        const wrapper = mountForm();
        const select = element(wrapper, "__input_section");
        expect(select.props("value")).toBe("__no_section__");
        expect(selectOptions(wrapper).map((o) => o.label)).toEqual([
            "None",
            "Advanced options",
            "references",
            "New section...",
        ]);
        expect(wrapper.findAllComponents(FormElement)).toHaveLength(1);
    });

    it("assigns the step to an existing section", () => {
        const wrapper = mountForm();
        element(wrapper, "__input_section").vm.$emit("input", "advanced");
        expect(wrapper.emitted("onUpdateStep")).toEqual([[3, { section: "advanced" }]]);
        expect(wrapper.emitted("onUpdateInputSections")).toBeUndefined();
    });

    it("creates a new section with an unused name", () => {
        const wrapper = mountForm(undefined, [{ name: "section_2" }]);
        element(wrapper, "__input_section").vm.$emit("input", "__new_section__");
        expect(wrapper.emitted("onUpdateInputSections")).toEqual([
            [[{ name: "section_2" }, { name: "section_3", label: "Section 3", expanded: false }]],
        ]);
        expect(wrapper.emitted("onUpdateStep")).toEqual([[3, { section: "section_3" }]]);
    });

    it("removes the step from its section", () => {
        const wrapper = mountForm("advanced");
        element(wrapper, "__input_section").vm.$emit("input", "__no_section__");
        expect(wrapper.emitted("onUpdateStep")).toEqual([[3, { section: undefined }]]);
    });

    it("edits the shared definition of the step's section", () => {
        const wrapper = mountForm("advanced");
        expect(element(wrapper, "__input_section_label").props("value")).toBe("Advanced options");
        expect(element(wrapper, "__input_section_expanded").props("value")).toBe(false);
        element(wrapper, "__input_section_label").vm.$emit("input", "Tuning");
        element(wrapper, "__input_section_expanded").vm.$emit("input", true);
        expect(wrapper.emitted("onUpdateInputSections")).toEqual([
            [[{ name: "advanced", label: "Tuning", expanded: false }, SECTIONS[1]]],
            [[{ name: "advanced", label: "Advanced options", expanded: true }, SECTIONS[1]]],
        ]);
    });

    it("defines a section the step references but the workflow does not", () => {
        const wrapper = mountForm("pasted", []);
        expect(selectOptions(wrapper).map((o) => o.value)).toEqual(["__no_section__", "pasted", "__new_section__"]);
        element(wrapper, "__input_section_label").vm.$emit("input", "Pasted inputs");
        expect(wrapper.emitted("onUpdateInputSections")).toEqual([
            [[{ name: "pasted", expanded: false, label: "Pasted inputs" }]],
        ]);
    });
});
