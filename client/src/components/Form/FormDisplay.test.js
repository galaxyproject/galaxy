import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import Vue from "vue";
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
            prefix: "",
            sustainRepeats: false,
            sustainConditionals: false,
            collapsedEnableText: "Enable",
            collapsedDisableText: "Disable",
            collapsedEnableIcon: "fa fa-caret-square-o-down",
            collapsedDisableIcon: "fa fa-caret-square-o-up",
            validationScrollTo: [],
            replaceParams: {},
        };
        wrapper = mount(FormDisplay, {
            propsData,
            localVue,
            stubs: {},
        });
    });

    it("props", async () => {
        await wrapper.setProps({
            validationScrollTo: ["name", "error_message"],
        });
        const error = wrapper.find(".ui-form-error-text");
        expect(error.text()).toEqual("error_message");
    });
});
