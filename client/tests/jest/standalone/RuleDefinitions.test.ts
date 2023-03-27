import RuleDefs from "@/components/RuleBuilder/rule-definitions";
import SPEC_TEST_CASES from "./rules_dsl_spec.yml";

function applyRules(rules: Array<any>, data: Array<Array<string>>, sources: Array<number>) {
    const columns = Array(data[0]?.length).fill("new");
    return RuleDefs.applyRules(data, sources, columns, rules);
}

interface State {
    data: Array<Array<string>>;
    sources: Array<number>;
}

interface SpecTestCase {
    doc?: string;
    rules: Array<any>;
    error?: boolean;
    initial?: State;
    final?: State;
}

function itShouldConform(specTestCase: SpecTestCase, i: number) {
    let doc = "";
    if (specTestCase.doc) {
        doc = " - " + specTestCase.doc;
    }
    it(`should pass conformance test case ${i} (from rules_dsl_spec.yml) ${doc}`, () => {
        expect(specTestCase).toHaveProperty("rules");
        if (specTestCase.initial) {
            expect(specTestCase).toHaveProperty("final");

            const result = applyRules(specTestCase.rules, specTestCase.initial.data, specTestCase.initial.sources);
            const finalData = specTestCase.final?.data;
            const finalSources = specTestCase.final?.sources;
            expect(result.data).toEqual(finalData);
            if (finalSources !== undefined) {
                expect(result.sources).toEqual(finalSources);
            }
        } else {
            expect(specTestCase.error).toBe(true);
            // TODO: test these...
        }
    });
}

describe("Rules DSL", () => {
    for (const [i, testCaseJson] of Object.entries(SPEC_TEST_CASES)) {
        const testCase: SpecTestCase = testCaseJson as SpecTestCase;
        itShouldConform(testCase, parseInt(i));
    }
});
