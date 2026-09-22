import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { PiniaVuePlugin } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useRefreshFromStore } from "@/stores/refreshFromStore";

import FormCollectionType from "./FormCollectionType.vue";
import FormDefault from "./FormDefault.vue";
import FormInputCollection from "./FormInputCollection.vue";

vi.mock("./FormDatatype.vue", () => ({ default: { render: (h) => h("div") } }));

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

describe("FormDefault", () => {
    let wrapper;
    const outputs = [
        { name: "output-name", label: "output-label" },
        { name: "other-name", label: "other-label" },
    ];

    beforeEach(() => {
        wrapper = mount(FormDefault, {
            propsData: {
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
            localVue,
            pinia: createTestingPinia({ createSpy: vi.fn }),
            provide: {
                workflowId: "mock-workflow",
            },
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
            localVue,
            pinia: createTestingPinia({ createSpy: vi.fn, stubActions: false }),
            provide: { workflowId: "mock-workflow" },
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
        collectionWrapper.destroy();
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
});
