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
                    name: "name",
                    type: "text",
                    value: "value",
                    help: "help",
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
            validationScrollTo: ["name", "error_message"],
        });
        const error = wrapper.find(".ui-form-error-text");
        expect(error.text()).toEqual("error_message");
        await wrapper.setProps({
            errors: { name: "error_message_2" },
        });
        expect(error.text()).toEqual("error_message_2");
    });

    it("parameter replacement", async () => {
        const input = wrapper.find("[id='field-name']");
        expect(input.element.value).toEqual("value");
        await wrapper.setProps({
            replaceParams: { name: "replaced" },
        });
        expect(input.element.value).toEqual("replaced");
    });
});
