import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import FormDefault from "./FormDefault";
import { createTestingPinia } from "@pinia/testing";
import { PiniaVuePlugin } from "pinia";

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
                    type: "subworkflow",
                    configForm: {
                        inputs: [],
                    },
                    inputs: [],
                    outputs,
                },
            },
            localVue,
            pinia: createTestingPinia(),
        });
    });

    it("check initial value and value change", async () => {
        const title = wrapper.find(".portlet-title-text").text();
        expect(title).toBe("label");
        const inputCount = wrapper.findAll("input").length;
        expect(inputCount).toBe(4);
        const outputLabelCount = wrapper.findAll("#__label__output-name").length;
        expect(outputLabelCount).toBe(1);
        const otherLabelCount = wrapper.findAll("#__label__other-name").length;
        expect(otherLabelCount).toBe(1);
    });
});
