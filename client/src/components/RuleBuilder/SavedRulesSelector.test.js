import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import SavedRulesSelector from "@/components/RuleBuilder/SavedRulesSelector.vue";

const localVue = getLocalVue();

enableAutoUnmount(afterEach);

function mountSelector() {
    return mount(SavedRulesSelector, {
        props: { savedRules: [] },
        global: localVue,
    });
}

function savedRule(dateTime, column = 0) {
    return {
        dateTime,
        rule: JSON.stringify({
            rules: [{ type: "add_filter_count", count: 1, which: "first", invert: false }],
            mapping: [{ type: "url", columns: [column] }],
        }),
    };
}

describe("SavedRulesSelector", () => {
    it("disables the history icon when there are no saved rules", () => {
        const wrapper = mountSelector();
        expect(wrapper.get("#savedRulesButton").classes()).toContain("disabled");
    });

    it("emits the selected saved rule when its session is clicked", async () => {
        const wrapper = mountSelector();
        const session = savedRule("2021-12-12T12:12:12.000Z");
        await wrapper.setProps({ savedRules: [session] });

        const sessions = wrapper.findAll("div.dropdown-menu > a.saved-rule-item");
        expect(sessions).toHaveLength(1);
        await sessions[0].trigger("click");
        expect(wrapper.emitted("update-rules")).toEqual([[session.rule]]);
    });

    it("lists the newest saved rule first and emits it once when clicked", async () => {
        const wrapper = mountSelector();
        const older = savedRule("2021-12-12T12:12:12.000Z");
        const newer = savedRule("2021-12-22T12:12:12.000Z", 1);
        await wrapper.setProps({ savedRules: [older, newer] });

        const sessions = wrapper.findAll("div.dropdown-menu > a.saved-rule-item");
        expect(sessions).toHaveLength(2);
        await sessions[0].trigger("click");

        const emitted = wrapper.emitted("update-rules");
        expect(emitted).toBeTruthy();
        expect(emitted).toHaveLength(1);
        expect(emitted[0]).toEqual([newer.rule]);
    });
});
