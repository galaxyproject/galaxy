import chai from "chai";
import RuleDefs from "mvc/rules/rule-definitions";
import SPEC_TEST_CASES from "json-loader!yaml-loader!./rules_dsl_spec.yml";

const RULES = RuleDefs.RULES;

function applyRules(rules, data, sources) {
    let columns = [];
    if (data[0]) {
        for (const index in data[0]) {
            columns.push("new");
        }
    }
    for (var ruleIndex in rules) {
        const rule = rules[ruleIndex];
        rule.error = null;
        rule.warn = null;

        var ruleType = rule.type;
        const ruleDef = RULES[ruleType];
        const res = ruleDef.apply(rule, data, sources, columns);
        if (res.error) {
            throw res.error;
        } else {
            if (res.warn) {
                rule.warn = res.warn;
            }
            data = res.data || data;
            sources = res.sources || sources;
            columns = res.columns || columns;
        }
    }
    return { data, sources, columns };
}

function itShouldConform(specTestCase, i) {
    it("should pass conformance test case " + i, function() {
        chai.assert.property(specTestCase, "rules");
        chai.assert.property(specTestCase, "initial");
        chai.assert.property(specTestCase, "final");

        const rules = specTestCase.rules;
        const initial = specTestCase.initial;
        const expectedFinal = specTestCase.final;

        const final = applyRules(rules, initial.data, initial.sources);
        const finalData = final.data;
        const finalSources = final.sources;
        chai.assert.deepEqual(finalData, expectedFinal.data);
        if (expectedFinal.sources !== undefined) {
            chai.assert.deepEqual(finalSources, expectedFinal.sources);
        }
    });
}

describe("Rules DSL Spec", function() {
    SPEC_TEST_CASES.forEach(itShouldConform);
});
