import RuleDefs from "mvc/rules/rule-definitions";
import SPEC_TEST_CASES from "json-loader!yaml-loader!./rules_dsl_spec.yml";

function applyRules(rules, data, sources) {
    const columns = [];
    if (data[0]) {
        for (const index in data[0]) {
            columns.push("new");
        }
    }
    return RuleDefs.applyRules(data, sources, columns, rules);
}

function itShouldConform(specTestCase, i) {
    let doc = "";
    if (specTestCase.doc) {
        doc = " - " + specTestCase.doc;
    }
    it("should pass conformance test case " + i + " (from rules_dsl_spec.yml)" + doc, function () {
        expect(specTestCase).to.have.property("rules");
        if (specTestCase.initial) {
            expect(specTestCase).to.have.property("final");

            const rules = specTestCase.rules;
            const initial = specTestCase.initial;
            const expectedFinal = specTestCase.final;

            const final = applyRules(rules, initial.data, initial.sources);
            const finalData = final.data;
            const finalSources = final.sources;
            expect(finalData).to.deep.equal(expectedFinal.data);
            if (expectedFinal.sources !== undefined) {
                expect(finalSources).to.deep.equal(expectedFinal.sources);
            }
        } else {
            expect(specTestCase.error).to.be.true;
            // TODO: test these...
        }
    });
}

describe("Rules DSL", function () {
    SPEC_TEST_CASES.forEach(itShouldConform);
});
