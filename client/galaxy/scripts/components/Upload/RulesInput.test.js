import RulesInput from "./RulesInput.vue";
import { mountWithApp } from "./test_helpers";

describe("RulesInput.vue", () => {
    it("loads with correct initial state", async () => {
        const { wrapper } = mountWithApp(RulesInput);
    });
});
