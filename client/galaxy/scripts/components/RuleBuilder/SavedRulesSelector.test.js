import Vue from "vue";
import { mount } from "@vue/test-utils";
import SavedRulesSelector from "components/RuleBuilder/SavedRulesSelector";

describe("SavedRulesSelector", () => {
    it("disables history icon if there is no history", () => {
        const wrapper = mount(SavedRulesSelector, {
            propsData: {
                numOfSavedRules: 0,
            },
        });
        expect(wrapper.find("#savedRulesButton").classes()).to.contain("disabled");
    });

    it("saves a session and loads it", () => {
        expect();
    });
});
