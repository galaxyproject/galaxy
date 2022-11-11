import RuleDefs from "components/RuleBuilder/rule-definitions";
import SPEC_TEST_CASES from "./rules_dsl_spec.yml";

function applyRules(rules, data, sources) {
    const columns = Array(data[0].length).fill("new");
    return RuleDefs.applyRules(data, sources, columns, rules);
}

class State {
    data: Array<Array<string>>
    sources: Array<number>
}

class SpecTestCase {
    doc?: string
    rules: Array<any>
    error?: boolean
    initial?: State
    final?: State
}

function itShouldConform(specTestCase: SpecTestCase, i: number) {
    let doc = "";
    if (specTestCase.doc) {
        doc = " - " + specTestCase.doc;
    }
    it(`should pass conformance test case ${ i } (from rules_dsl_spec.yml) ${ doc }`, () => {
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
    for (const [i, testCaseJson] of Object.entries(SPEC_TEST_CASES)) {
        const testCase:SpecTestCase = Object.assign(new SpecTestCase(), testCaseJson);
        itShouldConform(testCase, parseInt(i));
    }
});
