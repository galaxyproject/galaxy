import { faCaretSquareDown, faCaretSquareUp } from "@fortawesome/free-regular-svg-icons";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it } from "vitest";

import FormDisplay from "./FormDisplay.vue";

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
            collapsedEnableIcon: faCaretSquareDown,
            collapsedDisableIcon: faCaretSquareUp,
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

describe("FormDisplay repeat cloning", () => {
    const TEXT_REPEAT = [{ type: "text", name: "t" }];

    function mountWithRepeat(repeatInputs, repeatAttrs = {}) {
        return mount(FormDisplay, {
            propsData: {
                id: "input",
                inputs: [
                    {
                        type: "repeat",
                        name: "repeat_block",
                        title: "Repeat Block",
                        inputs: repeatInputs,
                        ...repeatAttrs,
                    },
                ],
                errors: {},
                validationScrollTo: [],
                replaceParams: {},
                prefix: "",
                sustainRepeats: false,
                sustainConditionals: false,
            },
            localVue,
        });
    }

    async function insert(wrapper, count) {
        const button = wrapper.find("[data-description='repeat insert']");
        for (let i = 0; i < count; i++) {
            await button.trigger("click");
        }
        await flushPromises();
    }

    function valuesOf(wrapper, count) {
        return [...Array(count).keys()].map((i) => wrapper.find(`[id='repeat_block_${i}|t']`).element.value);
    }

    it("inserts the copy after its source and leaves the two independent", async () => {
        const wrapper = mountWithRepeat(TEXT_REPEAT);
        await insert(wrapper, 3);
        await wrapper.find("[id='repeat_block_0|t']").setValue("A");
        await wrapper.find("[id='repeat_block_1|t']").setValue("B");
        await wrapper.find("[id='repeat_block_2|t']").setValue("C");

        await wrapper.find("#repeat_block_1_clone").trigger("click");
        await flushPromises();

        expect(wrapper.findAll("[data-description='repeat block']").length).toBe(4);
        expect(valuesOf(wrapper, 4)).toEqual(["A", "B", "B", "C"]);

        // Editing either copy must not reach the other -- structuredClone, not a shared ref.
        await wrapper.find("[id='repeat_block_2|t']").setValue("B2");
        expect(valuesOf(wrapper, 4)).toEqual(["A", "B", "B2", "C"]);
        await wrapper.find("[id='repeat_block_1|t']").setValue("B1");
        expect(valuesOf(wrapper, 4)).toEqual(["A", "B1", "B2", "C"]);
    });

    it("re-keys the emitted form data after a middle block is cloned", async () => {
        const wrapper = mountWithRepeat(TEXT_REPEAT);
        await insert(wrapper, 2);
        await wrapper.find("[id='repeat_block_0|t']").setValue("A");
        await wrapper.find("#repeat_block_0_clone").trigger("click");
        await flushPromises();

        const formData = wrapper.emitted("onChange").at(-1)[0];
        expect(Object.keys(formData).sort()).toEqual(["repeat_block_0|t", "repeat_block_1|t", "repeat_block_2|t"]);
        expect(formData["repeat_block_1|t"]).toBe("A");
    });

    it("clones a block containing a conditional", async () => {
        const wrapper = mountWithRepeat([
            {
                type: "conditional",
                name: "cond",
                test_param: { name: "sel", type: "boolean", value: "true", help: "" },
                cases: [
                    { value: "true", inputs: [{ type: "text", name: "in_b" }] },
                    { value: "false", inputs: [] },
                ],
            },
        ]);
        await insert(wrapper, 1);
        await wrapper.find("[id='repeat_block_0|cond|in_b']").setValue("hello");

        await wrapper.find("#repeat_block_0_clone").trigger("click");
        await flushPromises();

        expect(wrapper.find("[id='repeat_block_1|cond|in_b']").element.value).toBe("hello");
        await wrapper.find("[id='repeat_block_1|cond|in_b']").setValue("world");
        expect(wrapper.find("[id='repeat_block_0|cond|in_b']").element.value).toBe("hello");
    });

    it("clones a block containing a nested repeat", async () => {
        const wrapper = mountWithRepeat([
            { type: "repeat", name: "inner", title: "Inner", inputs: [{ type: "text", name: "t" }] },
        ]);
        await insert(wrapper, 1);
        const innerInsert = () =>
            wrapper.findAll("[data-description='repeat insert']").wrappers.find((w) => w.text() === "Insert Inner");
        await innerInsert().trigger("click");
        await flushPromises();
        await innerInsert().trigger("click");
        await flushPromises();
        await wrapper.find("[id='repeat_block_0|inner_0|t']").setValue("X");
        await wrapper.find("[id='repeat_block_0|inner_1|t']").setValue("Y");

        await wrapper.find("#repeat_block_0_clone").trigger("click");
        await flushPromises();

        expect(wrapper.find("[id='repeat_block_1|inner_0|t']").element.value).toBe("X");
        expect(wrapper.find("[id='repeat_block_1|inner_1|t']").element.value).toBe("Y");
        await wrapper.find("[id='repeat_block_1|inner_0|t']").setValue("Z");
        expect(wrapper.find("[id='repeat_block_0|inner_0|t']").element.value).toBe("X");
    });

    it("refuses to clone once max is reached", async () => {
        const wrapper = mountWithRepeat(TEXT_REPEAT, { max: 2 });
        await insert(wrapper, 2);

        const cloneButton = wrapper.find("#repeat_block_0_clone");
        expect(cloneButton.attributes("aria-disabled")).toBe("true");
        await cloneButton.trigger("click");
        await flushPromises();
        expect(wrapper.findAll("[data-description='repeat block']").length).toBe(2);
    });

    it("keeps the cloned values across a server round-trip", async () => {
        const wrapper = mountWithRepeat(TEXT_REPEAT);
        await insert(wrapper, 2);
        await wrapper.find("[id='repeat_block_0|t']").setValue("A");
        await wrapper.find("[id='repeat_block_1|t']").setValue("B");
        await wrapper.find("#repeat_block_0_clone").trigger("click");
        await flushPromises();
        expect(valuesOf(wrapper, 3)).toEqual(["A", "A", "B"]);

        // The build response comes back describing three blocks; syncInputsStructural matches
        // the repeat cache positionally, so the clone has to survive it.
        await wrapper.setProps({
            inputs: [
                {
                    type: "repeat",
                    name: "repeat_block",
                    title: "Repeat Block",
                    inputs: TEXT_REPEAT,
                    cache: [
                        [{ type: "text", name: "t", value: "A" }],
                        [{ type: "text", name: "t", value: "A" }],
                        [{ type: "text", name: "t", value: "B" }],
                    ],
                },
            ],
        });
        await flushPromises();
        expect(valuesOf(wrapper, 3)).toEqual(["A", "A", "B"]);
    });
});
