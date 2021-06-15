import RuleDefs from "mvc/rules/rule-definitions";
import SPEC_TEST_CASES from "./rules_dsl_spec.yml";

function applyRules(rules, data, sources) {
    const columns = Array(data[0].length).fill("new");
    return RuleDefs.applyRules(data, sources, columns, rules);
}

function itShouldConform(specTestCase, i) {
    let doc = "";
    if (specTestCase.doc) {
        doc = " - " + specTestCase.doc;
    }
    it("should pass conformance test case " + i + " (from rules_dsl_spec.yml)" + doc, () => {
        expect(specTestCase).toHaveProperty("rules");
        if (specTestCase.initial) {
            expect(specTestCase).toHaveProperty("final");

            const result = applyRules(specTestCase.rules, specTestCase.initial.data, specTestCase.initial.sources);

            expect(result.data).toEqual(specTestCase.final.data);
            if (specTestCase.final.sources !== undefined) {
                expect(result.sources).toEqual(specTestCase.final.sources);
            }
        } else {
            expect(specTestCase.error).toBe(true);
            // TODO: test these...
        }
    });
}

describe("Rules DSL", () => {
    for (const [i, rule] of Object.entries(SPEC_TEST_CASES)) {
        itShouldConform(rule, i);
    }
});
