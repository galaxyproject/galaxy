import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import SavedRulesSelector from "components/RuleBuilder/SavedRulesSelector";

const localVue = getLocalVue();

describe("SavedRulesSelector", () => {
    let wrapper;
    let emitted;

    beforeEach(async () => {
        wrapper = mount(SavedRulesSelector, {
            propsData: {
                // Add a unique prefix for this test run so the test is not affected by local storage values
                prefix: "test_prefix_" + new Date().toISOString() + "_",
                savedRules: [],
                ruleColHeaders: [],
            },
            localVue,
        });
        await wrapper.vm.$nextTick();
    });

    afterEach(async () => {
        await wrapper.vm.$nextTick();
    });

    it("disables history icon if there is no history", async () => {
        // Expect button to be disabled if we haven't saved a session
        expect(wrapper.find("#savedRulesButton").classes()).toContain("disabled");
    });

    it("should emit a click event when a session is clicked", async () => {
        const testRules = {
            rules: [
                {
                    type: "add_filter_count",
                    count: 1,
                    which: "first",
                    invert: false,
                },
            ],
            mapping: [
                {
                    type: "url",
                    columns: [0],
                },
            ],
        };
        const ruleHeaders = ["A"];
        const dateTime = new Date().toISOString();
        await wrapper.setProps({
            user: "test_user",
            savedRules: [{ dateTime: dateTime, rule: JSON.stringify(testRules) }],
            ruleColHeaders: [ruleHeaders],
        });
        const sessions = wrapper.findAll("div.dropdown-menu > a.saved-rule-item");
        expect(sessions.length > 0).toBeTruthy();
        sessions.wrappers[0].trigger("click");
        emitted = wrapper.emitted();
        expect(emitted["update-rules"]).toBeTruthy();
    });

    it("should sort rules based on time created", async () => {
        //created less recently 12/12/2021
        const firstRule = {
            rules: [
                {
                    type: "add_filter_count",
                    count: 1,
                    which: "first",
                    invert: false,
                },
            ],
            mapping: [
                {
                    type: "url",
                    columns: [0],
                },
            ],
        };
        const testRules1 = {
            rule: JSON.stringify(firstRule),
            dateTime: "2021-12-12T12:12:12.000Z",
        };
        //created more recently 12/22/2021
        const secondRule = {
            rules: [
                {
                    type: "add_filter_count",
                    count: 1,
                    which: "first",
                    invert: false,
                },
            ],
            mapping: [
                {
                    type: "url",
                    columns: [1],
                },
            ],
        };
        const testRules2 = {
            rule: JSON.stringify(secondRule),
            dateTime: "2021-12-22T12:12:12.000Z",
        };
        await wrapper.setProps({
            user: "test_user",
            savedRules: [testRules1, testRules2],
        });
        const sessions = wrapper.findAll("div.dropdown-menu > a.saved-rule-item");
        expect(sessions.length == 2).toBeTruthy();
        //clicking the top result of the dropdown, with sorting should be most recent created rules
        sessions.wrappers[0].trigger("click");
        emitted = wrapper.emitted();
        expect(emitted["update-rules"]).toBeTruthy();
        expect(emitted["update-rules"].length).toBe(1);
        //ensure the object sent with emit is equal to most recent rule set
        expect(emitted["update-rules"][0]).toEqual([testRules2.rule]);
    });
});
