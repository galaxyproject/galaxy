import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import FormDisplay from "./FormDisplay";

const localVue = getLocalVue();

describe("FormDisplay", () => {
    let wrapper;
    let propsData;

    beforeEach(() => {
        propsData = {
            id: "input",
            inputs: [
                {
                    name: "text_name",
                    value: "text_value",
                    help: "text_help",
                    type: "text",
                },
                {
                    type: "conditional",
                    name: "conditional_section",
                    test_param: {
                        name: "conditional_bool",
                        label: "conditional_bool_label",
                        type: "boolean",
                        value: "true",
                        help: "",
                    },
                    cases: [
                        {
                            value: "true",
                            inputs: [
                                {
                                    name: "conditional_leaf",
                                    value: "conditional_leaf_value",
                                    type: "text",
                                },
                            ],
                        },
                        {
                            value: "false",
                            inputs: [],
                        },
                    ],
                },
                {
                    type: "repeat",
                    name: "repeat_block",
                    title: "Repeat Block",
                    help: "repeat help",
                    inputs: [
                        {
                            type: "text",
                            name: "repeat_text_a",
                        },
                        {
                            type: "text",
                            name: "repeat_text_b",
                        },
                    ],
                },
                {
                    type: "section",
                    name: "section_block",
                    title: "Section Block",
                    help: "section help",
                    inputs: [
                        {
                            type: "text",
                            name: "section_text_a",
                        },
                        {
                            type: "text",
                            name: "section_text_b",
                        },
                    ],
                },
            ],
            errors: {},
            validationScrollTo: [],
            replaceParams: {},
            prefix: "",
            sustainRepeats: false,
            sustainConditionals: false,
            collapsedEnableText: "Enable",
            collapsedDisableText: "Disable",
            collapsedEnableIcon: "collapsedEnableIcon",
            collapsedDisableIcon: "collapsedDisableIcon",
        };
        wrapper = mount(FormDisplay, {
            propsData,
            localVue,
            stubs: {},
        });
    });

    it("error highlighting", async () => {
        await wrapper.setProps({
            validationScrollTo: ["text_name", "error_message"],
        });
        const error = wrapper.find(".ui-form-error-text");
        expect(error.text()).toEqual("error_message");
        await wrapper.setProps({
            errors: { text_name: "error_message_2" },
        });
        expect(error.text()).toEqual("error_message_2");
    });

    it("parameter replacement", async () => {
        const textInput = wrapper.find("#text_name");
        const conditionalInput = wrapper.find("[id='conditional_section|conditional_leaf']");
        expect(textInput.element.value).toEqual("text_value");
        expect(conditionalInput.element.value).toEqual("conditional_leaf_value");
        await wrapper.setProps({
            replaceParams: {
                text_name: "replaced",
                "conditional_section|conditional_leaf": "conditional_leaf_value_new",
            },
        });
        expect(textInput.element.value).toEqual("replaced");
        expect(conditionalInput.element.value).toEqual("conditional_leaf_value_new");
    });

    it("conditional switch", async () => {
        const conditionalBool = wrapper.find("[type='checkbox']");
        await conditionalBool.setChecked(false);
        const conditionalInputUnchecked = wrapper.findAll("[id='conditional_section|conditional_leaf']");
        expect(conditionalInputUnchecked.length).toEqual(0);
        await conditionalBool.setChecked(true);
        const conditionalInputChecked = wrapper.findAll("[id='conditional_section|conditional_leaf']");
        expect(conditionalInputChecked.length).toEqual(1);
        await wrapper.setProps({
            sustainConditionals: true,
        });
        const conditionalBoolDisabled = wrapper.findAll("[type='checkbox']");
        expect(conditionalBoolDisabled.length).toEqual(0);
    });

    it("repeats", async () => {
        const repeatButton = wrapper.find("[data-description='repeat insert']");
        expect(repeatButton.text()).toBe("Insert Repeat Block");
        const repeatHelp = wrapper.find("[data-description='repeat help']").exists();
        expect(repeatHelp).toBeTruthy();
        for (let i = 0; i < 3; i++) {
            const repeatBlocks = wrapper.findAll("[data-description='repeat block']").length;
            expect(repeatBlocks).toBe(i);
            await repeatButton.trigger("click");
        }
    });

    it("section", async () => {
        const sectionHelpText = wrapper.find("[data-description='section help']").text();
        expect(sectionHelpText).toBe("section help");
    });
});
