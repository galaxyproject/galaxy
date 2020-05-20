import Vue from "vue";
import { mount } from "@vue/test-utils";
import SavedRulesSelector from "components/RuleBuilder/SavedRulesSelector";

describe("SavedRulesSelector", () => {

  let wrapper, emitted;
  beforeEach(async () => {
    wrapper = mount(SavedRulesSelector);
    emitted = wrapper.emitted();
    await Vue.nextTick();
  });

  it("disables history icon if there is no history", async () => {
    wrapper = mount(SavedRulesSelector, {
      propsData: {
        numOfSavedRules: 0,
      },
    });
    await Vue.nextTick();
    expect(wrapper.find("#savedRulesButton").classes()).to.contain("disabled");
  });

  it("should emit a click event when a session is clicked", async () => {
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

    wrapper.vm.saveSession(testRules);
    await Vue.nextTick();
    let session = wrapper.find("div.dropdown-menu > a.saved-rule-item");
    session.trigger("click");
    assert(emitted["update-rules"], "click event not detected");

  });

});
