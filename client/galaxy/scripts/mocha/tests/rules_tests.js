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
    return RuleDefs.applyRules(data, sources, columns, rules);
}

function itShouldConform(specTestCase, i) {
    it("should pass conformance test case " + i, function() {
        chai.assert.property(specTestCase, "rules");
        if (specTestCase.initial) {
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
        } else {
            chai.assert(specTestCase.error);
            // TODO: test these...
        }
    });
}

describe("Rules DSL Spec", function() {
    SPEC_TEST_CASES.forEach(itShouldConform);
});
