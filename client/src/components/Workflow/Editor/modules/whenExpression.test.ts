import { describe, expect, it } from "vitest";

import GENERATED_PRESENCE_CONDITIONS from "./generated_presence_conditions.yml";
import EXPRESSION_SPECIFICATIONS from "./when_expression_spec.yml";
import {
    analyzeInputReferences,
    classifyWhenInputIsNull,
    expressionGuardsInputPresence,
    expressionReferencesInput,
    type NullBehavior,
    presenceGateExpression,
} from "./whenExpression";
import type { InputPath } from "./workflowInputPath";

type InputTarget = string | InputPath;

interface ExpressionExpectations {
    static_paths?: InputPath[];
    dynamic?: boolean;
    references_input?: boolean;
    null_behavior?: NullBehavior;
    guards_presence?: boolean;
}

interface ExpressionSpecification {
    doc: string;
    expression: string;
    input?: InputTarget;
    expect: ExpressionExpectations;
}

interface GeneratedConditionSpecification {
    doc: string;
    input: InputTarget;
    expression: string;
}

const EXPRESSIONS = EXPRESSION_SPECIFICATIONS as ExpressionSpecification[];
const GENERATED_CONDITIONS = GENERATED_PRESENCE_CONDITIONS as GeneratedConditionSpecification[];

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
            if (expected.null_behavior !== undefined) {
                expect(classifyWhenInputIsNull(expression, requireInput(specification))).toBe(expected.null_behavior);
            }
            if (expected.guards_presence !== undefined) {
                expect(expressionGuardsInputPresence(expression, requireInput(specification))).toBe(
                    expected.guards_presence,
                );
            }
        });
    }
});

describe("generated presence conditions", () => {
    for (const specification of GENERATED_CONDITIONS) {
        it(specification.doc, () => {
            const expression = presenceGateExpression(specification.input);
            expect(expression).toBe(specification.expression);
            expect(expressionReferencesInput(expression, specification.input)).toBe(true);
            expect(classifyWhenInputIsNull(expression, specification.input)).toBe("false-when-null");
            expect(expressionGuardsInputPresence(expression, specification.input)).toBe(true);
        });
    }
});

describe("analyzer failure boundaries", () => {
    it("returns conservative answers when no expression is present", () => {
        expect(expressionReferencesInput(undefined, "input1")).toBe(false);
        expect(expressionGuardsInputPresence(undefined, "input1")).toBe(false);
        expect(classifyWhenInputIsNull(undefined, "input1")).toBe("unknown");
    });

    it("survives an expression deep enough to exhaust the stack", () => {
        const deep = `$(${"(".repeat(20000)}inputs.a${")".repeat(20000)} !== null)`;
        expect(() => classifyWhenInputIsNull(deep, "a")).not.toThrow();
        expect(classifyWhenInputIsNull(deep, "a")).toBe("unknown");
        expect(() => expressionGuardsInputPresence(deep, "a")).not.toThrow();
    });
});
