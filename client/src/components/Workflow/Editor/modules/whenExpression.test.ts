import { describe, expect, it } from "vitest";

import EXPRESSION_SPECIFICATIONS from "./when_expression_spec.yml";
import { analyzeInputReferences, expressionReferencesInput } from "./whenExpression";
import type { InputPath } from "./workflowInputPath";

type InputTarget = string | InputPath;

interface ExpressionExpectations {
    static_paths?: InputPath[];
    dynamic?: boolean;
    references_input?: boolean;
}

interface ExpressionSpecification {
    doc: string;
    expression: string;
    input?: InputTarget;
    expect: ExpressionExpectations;
}

const EXPRESSIONS = EXPRESSION_SPECIFICATIONS as ExpressionSpecification[];

function requireInput(specification: ExpressionSpecification): InputTarget {
    if (specification.input === undefined) {
        throw new Error(`Specification '${specification.doc}' must declare an input`);
    }
    return specification.input;
}

describe("when expression specification", () => {
    for (const specification of EXPRESSIONS) {
        it(specification.doc, () => {
            const { expression, expect: expected } = specification;

            if (expected.static_paths !== undefined || expected.dynamic !== undefined) {
                const analysis = analyzeInputReferences(expression);
                if (expected.static_paths !== undefined) {
                    expect(analysis.staticPaths).toEqual(expected.static_paths);
                }
                if (expected.dynamic !== undefined) {
                    expect(analysis.hasDynamicInputsAccess).toBe(expected.dynamic);
                }
            }

            if (expected.references_input !== undefined) {
                expect(expressionReferencesInput(expression, requireInput(specification))).toBe(
                    expected.references_input,
                );
            }
        });
    }
});

describe("analyzer failure boundaries", () => {
    it("reports no references when no expression is present", () => {
        expect(expressionReferencesInput(undefined, "input1")).toBe(false);
    });
});
