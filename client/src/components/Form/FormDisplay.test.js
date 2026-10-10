import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { h } from "vue";

import FormData from "./Elements/FormData/FormData.vue";
import FormDisplay from "./FormDisplay.vue";

enableAutoUnmount(afterEach);

describe("FormDisplay", () => {
    let wrapper;

    beforeEach(() => {
        const propsData = {
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
        };
        wrapper = mount(FormDisplay, {
            propsData,
            global: getLocalVue(),
        });
    });

    it("replaces the highlighted validation error with a server error", async () => {
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

    it("replaces both a top-level value and an active conditional value", async () => {
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

    it("toggles conditional inputs and hides the switch when conditions are sustained", async () => {
        const conditionalBool = wrapper.find("[type='checkbox']");
        await conditionalBool.setValue(false);
        const conditionalInputUnchecked = wrapper.findAll("[id='conditional_section|conditional_leaf']");
        expect(conditionalInputUnchecked.length).toEqual(0);
        await conditionalBool.setValue(true);
        const conditionalInputChecked = wrapper.findAll("[id='conditional_section|conditional_leaf']");
        expect(conditionalInputChecked.length).toEqual(1);
        await wrapper.setProps({
            sustainConditionals: true,
        });
        const conditionalBoolDisabled = wrapper.findAll("[type='checkbox']");
        expect(conditionalBoolDisabled.length).toEqual(0);
    });

    it("inserts successive repeat blocks and shows their help", async () => {
        const repeatButton = wrapper.find("[data-description='repeat insert']");
        expect(repeatButton.text()).toBe("Insert Repeat Block");
        const repeatHelp = wrapper.find("[data-description='repeat help']").exists();
        expect(repeatHelp).toBeTruthy();
        for (let i = 0; i < 3; i++) {
            const repeatBlocks = wrapper.findAll("[data-description='repeat block']").length;
            expect(repeatBlocks).toBe(i);
            await repeatButton.trigger("click");
        }
        expect(wrapper.findAll("[data-description='repeat block']")).toHaveLength(3);
    });

    it("renders section help", async () => {
        const sectionHelpText = wrapper.find("[data-description='section help']").text();
        expect(sectionHelpText).toBe("section help");
    });
});

describe("FormDisplay repeated dataset events", () => {
    it.each(["data", "data_collection"])(
        "relays pagination and search events from repeated %s inputs",
        async (type) => {
            const input = { type, name: "input2", options: {} };
            const wrapper = mount(FormDisplay, {
                global: getLocalVue(),
                stubs: {
                    FormData: {
                        name: "FormData",
                        props: ["name"],
                        render: () => h("div"),
                    },
                },
                propsData: {
                    prefix: "section",
                    inputs: [
                        {
                            type: "repeat",
                            name: "queries",
                            title: "Dataset",
                            inputs: [input],
                            cache: [
                                [input],
                                [
                                    {
                                        type: "repeat",
                                        name: "nested",
                                        title: "Nested dataset",
                                        inputs: [input],
                                        cache: [[input]],
                                    },
                                ],
                            ],
                        },
                    ],
                },
            });
            await flushPromises();

            const selectors = wrapper.findAllComponents(FormData);
            expect(selectors.length).toBe(2);
            const names = ["section|queries_0|input2", "section|queries_1|nested_0|input2"];
            const src = type === "data" ? "hda" : "hdca";

            for (const [index, name] of names.entries()) {
                const selector = selectors.at(index);
                expect(selector.props("name")).toBe(name);

                const pagination = { name, src, offset: 50, limit: 50, search: "matching" };
                selector.vm.$emit("load-more", pagination);
                expect(wrapper.emitted("load-more")?.[index]).toEqual([pagination]);

                const search = { name, src, query: "matching", limit: 50 };
                selector.vm.$emit("search-change", search);
                expect(wrapper.emitted("search-change")?.[index]).toEqual([search]);
            }

            expect(wrapper.emitted("load-more")).toHaveLength(2);
            expect(wrapper.emitted("search-change")).toHaveLength(2);
        },
    );
});
