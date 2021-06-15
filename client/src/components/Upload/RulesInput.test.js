import RulesInput from "./RulesInput.vue";
import { mountWithApp } from "./testHelpers";

describe("RulesInput.vue", () => {
    it("loads with correct initial state", async () => {
        const { wrapper } = mountWithApp(RulesInput);
        expect(wrapper.find("#btn-reset").classes()).toEqual(expect.arrayContaining(["disabled"]));
    });
});
