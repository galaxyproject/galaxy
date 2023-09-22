import RulesInput from "./RulesInput.vue";
import { mountWithDetails } from "./testHelpers";

describe("RulesInput.vue", () => {
    it("loads with correct initial state", async () => {
        const { wrapper } = mountWithDetails(RulesInput);
        expect(wrapper.find("#btn-reset").classes()).toEqual(expect.arrayContaining(["disabled"]));
    });

    it("enables reset when sourceContent is populated", async () => {
        const { wrapper } = mountWithDetails(RulesInput);
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
