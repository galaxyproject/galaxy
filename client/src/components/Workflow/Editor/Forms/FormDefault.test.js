import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { h } from "vue";

import { useRefreshFromStore } from "@/stores/refreshFromStore";

import FormCollectionType from "./FormCollectionType.vue";
import FormDefault from "./FormDefault.vue";
import FormInputCollection from "./FormInputCollection.vue";
import FormElement from "@/components/Form/FormElement.vue";

vi.mock("./FormDatatype.vue", () => ({ default: { render: () => h("div") } }));

const localVue = getLocalVue();

describe("FormDefault", () => {
    let wrapper;
    const outputs = [
        { name: "output-name", label: "output-label" },
        { name: "other-name", label: "other-label" },
    ];

    beforeEach(() => {
        wrapper = mount(FormDefault, {
            props: {
                datatypes: [],
                step: {
                    id: 0,
                    contentId: "id",
                    annotation: "annotation",
                    label: "label",
                    name: "name",
                    type: "subworkflow",
                    configForm: {
                        inputs: [],
                    },
                    inputs: [],
                    outputs,
                },
            },
            global: { ...localVue, provide: { workflowId: "mock-workflow" } },
            pinia: createTestingPinia({ createSpy: vi.fn }),
        });
    });

    it("re-seeds the collection input form from the step on refresh", async () => {
        const collectionStep = {
            id: 0,
            content_id: null,
            annotation: "annotation",
            label: "label",
            name: "name",
            type: "data_collection_input",
            config_form: { inputs: [] },
            inputs: [],
            outputs: [],
            tool_state: { collection_type: '"list"' },
        };
        const collectionWrapper = mount(FormDefault, {
            propsData: { datatypes: [], step: collectionStep },
            global: { ...localVue, provide: { workflowId: "mock-workflow" } },
            pinia: createTestingPinia({ createSpy: vi.fn, stubActions: false }),
        });
        const collectionTypeField = () =>
            collectionWrapper.findComponent(FormInputCollection).findComponent(FormCollectionType);

        collectionTypeField().vm.$emit("onChange", "paired");
        await collectionWrapper.vm.$nextTick();
        expect(collectionTypeField().props("value")).toBe("paired");
        expect(collectionWrapper.emitted("onSetData")).toHaveLength(1);

        useRefreshFromStore().refresh();
        await collectionWrapper.vm.$nextTick();
        expect(collectionTypeField().props("value")).toBe("list");
        expect(collectionWrapper.emitted("onSetData")).toHaveLength(1);

        collectionTypeField().vm.$emit("onChange", "list:paired");
        expect(collectionWrapper.emitted("onSetData")).toHaveLength(2);
        expect(collectionWrapper.emitted("onSetData")[1][1].inputs.collection_type).toBe("list:paired");
        collectionWrapper.unmount();
    });

    it("check initial value and value change", async () => {
        const title = wrapper.find(".portlet-title-text").text();
        expect(title).toBe("name");
        const inputCount = wrapper.findAll("input").length;
        expect(inputCount).toBe(4);
        const outputLabelCount = wrapper.findAll("#__label__output-name").length;
        expect(outputLabelCount).toBe(1);
        const otherLabelCount = wrapper.findAll("#__label__other-name").length;
        expect(otherLabelCount).toBe(1);
    });

    it("edits and clears a file location while preserving other defaults and file metadata", async () => {
        const step = {
            id: 0,
            content_id: null,
            annotation: "",
            label: "input",
            name: "Input dataset",
            type: "data_input",
            config_form: { inputs: [] },
            inputs: [],
            outputs: [],
            tool_state: {},
            in: {
                input: { default: { class: "File", location: "https://example.org/old", format: "tabular" } },
                other: { default: 5 },
            },
        };
        const inputWrapper = mount(FormDefault, {
            propsData: { datatypes: [], step },
            global: { ...localVue, provide: { workflowId: "mock-workflow" } },
            pinia: createTestingPinia({ createSpy: vi.fn, stubActions: false }),
        });
        const field = inputWrapper
            .findAllComponents(FormElement)
            .find((component) => component.props("id") === "__default_location");
        expect(field.props("modelValue")).toBe("https://example.org/old");
        field.vm.$emit("update:modelValue", "https://example.org/new");
        const updated = inputWrapper.emitted("onUpdateStep")[0][1];
        expect(updated.in).toEqual({
            input: { default: { class: "File", location: "https://example.org/new", format: "tabular" } },
            other: { default: 5 },
        });
        await inputWrapper.setProps({ step: { ...step, ...updated } });
        field.vm.$emit("update:modelValue", "");
        expect(inputWrapper.emitted("onUpdateStep")[1][1].in).toEqual({ other: { default: 5 } });
        inputWrapper.unmount();
    });

    it("drops metadata describing the previous file when the location changes", () => {
        const step = {
            id: 0,
            content_id: null,
            annotation: "",
            label: "input",
            name: "Input dataset",
            type: "data_input",
            config_form: { inputs: [] },
            inputs: [],
            outputs: [],
            tool_state: {},
            in: {
                input: {
                    default: {
                        class: "File",
                        location: "https://example.org/old",
                        format: "tabular",
                        basename: "old.tsv",
                        MD5: "d41d8cd98f00b204e9800998ecf8427e",
                    },
                },
            },
        };
        const inputWrapper = mount(FormDefault, {
            propsData: { datatypes: [], step },
            global: { ...localVue, provide: { workflowId: "mock-workflow" } },
            pinia: createTestingPinia({ createSpy: vi.fn, stubActions: false }),
        });
        const field = inputWrapper
            .findAllComponents(FormElement)
            .find((component) => component.props("id") === "__default_location");
        field.vm.$emit("update:modelValue", "https://example.org/new");
        expect(inputWrapper.emitted("onUpdateStep")[0][1].in).toEqual({
            input: { default: { class: "File", location: "https://example.org/new", format: "tabular" } },
        });
        inputWrapper.unmount();
    });
});
