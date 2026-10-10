import { describe, expect, it } from "vitest";

import RuleDefs from "@/components/RuleBuilder/rule-definitions";

import SPEC_TEST_CASES from "./rules_dsl_spec.yml";

interface Rule {
    type: string;
    error?: string | null;
    warn?: string | null;
    [parameter: string]: unknown;
}

interface State {
    data: string[][];
    sources: Array<number | Record<string, unknown>>;
}

interface SpecTestCase {
    doc?: string;
    rules: Rule[];
    error?: boolean;
    initial?: State;
    final?: State;
}

const cases = (SPEC_TEST_CASES as SpecTestCase[]).map((spec, index) => ({
    ...spec,
    index,
    name: spec.doc ?? spec.rules.map((rule) => rule.type).join(", "),
}));

describe("Rules DSL", () => {
    it.each(cases)("shared specification case $index: $name", (spec) => {
        expect(spec).toHaveProperty("rules");
        if (!spec.initial) {
            // These six entries exercise backend schema validation. The client has
            // no RuleSet validator, and the specification supplies no data to apply.
            expect(spec.error).toBe(true);
            return;
        }

        // applyRules annotates rules and may sort metadata tags in place.
        const { data, sources } = structuredClone(spec.initial);
        const rules = structuredClone(spec.rules);
        const columns = Array(data[0]?.length ?? 0).fill("new");
        const result = RuleDefs.applyRules(data, sources, columns, rules);

        if (spec.error) {
            // Client runtime errors are returned on the rule rather than thrown.
            expect(rules.some((rule) => typeof rule.error === "string" && rule.error.length > 0)).toBe(true);
        } else {
            expect(spec).toHaveProperty("final");
            expect(rules.every((rule) => !rule.error)).toBe(true);
            expect(result.data).toEqual(spec.final?.data);
            if (spec.final?.sources !== undefined) {
                expect(result.sources).toEqual(spec.final.sources);
            }
        }
    });
});

describe("colHeadersFor", () => {
    it("returns an empty header list when there is no data and no columns", () => {
        // Callers map and index into the result, so it has to stay an array.
        expect(RuleDefs.colHeadersFor([], undefined)).toEqual([]);
    });
});
