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
        const wrapper = mount (SavedRulesSelector)
        const testRules = JSON.stringify({
            "rules": [
              {
                "type": "add_filter_count",
                "count": 1,
                "which": "first",
                "invert": false
              }
            ],
            "mapping": [
              {
                "type": "url",
                "columns": [
                  0
                ]
              }
            ]
          })

        wrapper.saveSession(testRules);

        expect(wrapper.find.getRules()).to.contain(testRules);
    });
});
