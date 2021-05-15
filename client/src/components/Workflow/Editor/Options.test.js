import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import Options from "./Options";

const localVue = getLocalVue();

describe("Options", () => {
    it("render properly", async () => {
        const wrapper = shallowMount(Options, {
            propsData: { hasChanges: true },
            localVue,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".editor-button-save").attributes("role")).toBe("button");
        expect(wrapper.find(".editor-button-save").attributes("disabled")).toBeFalsy();
        expect(wrapper.find(".editor-button-save-group").attributes("title")).toBe("Save Workflow");

        // requires a non-shallow mount
        // wrapper.find('.editor-button-attributes').trigger('click');
        // expect(wrapper.emitted().onAttributes).toBeTruthy();
    });

    it("should disable save if no changes", async () => {
        const wrapper = shallowMount(Options, {
            propsData: { hasChanges: false },
            localVue,
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".editor-button-save").attributes("disabled")).toBe("true");
    });
});
