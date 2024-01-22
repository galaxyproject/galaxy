import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import mountTarget from "./RulesInput.vue";

const localVue = getLocalVue();

function getWrapper() {
    return mount(mountTarget, {
        propsData: {
            fileSourcesConfigured: true,
            ftpUploadSite: null,
            historyId: "historyId",
        },
        localVue,
    });
}

describe("RulesInput", () => {
    it("rendering and reset", async () => {
        const wrapper = getWrapper();
        expect(wrapper.find("#btn-reset").classes()).toEqual(expect.arrayContaining(["disabled"]));
        const textInput = wrapper.find(".upload-rule-source-content");
        expect(textInput.element.value).toBe("");
        await textInput.setValue("a b c d");
        expect(textInput.element.value).toBe("a b c d");
        expect(wrapper.find("#btn-reset").classes()).not.toEqual(expect.arrayContaining(["disabled"]));
        await wrapper.find("#btn-reset").trigger("click");
        expect(textInput.element.value).toBe("");
        expect(wrapper.find("#btn-reset").classes()).toEqual(expect.arrayContaining(["disabled"]));
    });
});
