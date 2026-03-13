import { describe, expect, it } from "vitest";

import SPEC_PARAMETERS from "./parameter_models.yml";
import SPEC_TESTS from "./parameter_specification.yml";
import type { IntegerParameterModel } from "./parameterModels";
import { structuredInputs, type ToolParameterModel, validate } from "./structured";

describe("structured.js", () => {
    it("should parse galaxy integer parameters", () => {
        expect(true).toBe(true);
        const parameterModel: IntegerParameterModel = {
            name: "parameter",
            parameter_type: "gx_integer",
            optional: false,
            type: "integer",
        };
        const si = structuredInputs({ parameter: "5" }, [parameterModel]);
        expect(si).toHaveProperty("parameter");
        if ("parameter" in si) {
            const val = si["parameter"];
            expect(val).toBe(5);
        }
    });
});

type TestCase = { [ParameterName: string]: any };

interface FileTestCases {
    request_invalid: Array<TestCase>;
    request_valid: Array<TestCase>;
}

type ParameterSpecification = { [FileName: string]: FileTestCases };

function itShouldValidateParameters(file: string, parameters: Array<TestCase>) {
    for (const [index, parameter] of parameters.entries()) {
        itShouldValidateParameter(file, index, parameter);
    }
}

function itShouldInvalidateParameters(file: string, parameters: Array<TestCase>) {
    for (const [index, parameter] of parameters.entries()) {
        itShouldInvalidateParameter(file, index, parameter);
    }
}

function parameterModelsForFile(filename: string): Array<ToolParameterModel> {
    const parameterBundle = SPEC_PARAMETERS[filename];
    if (!parameterBundle || !parameterBundle.parameters) {
        return [];
    }
    return parameterBundle.parameters;
}

// List of test files to skip (e.g., tests that require complex Python expression evaluation)
const SKIP_TEST_FILES = new Set(["gx_text_expression_validation"]);

function itShouldValidateParameter(file: string, index: number, parameterTestCase: TestCase) {
    let doc = " for file [" + file + "] and valid parameter combination [" + index + "]";
    if (parameterTestCase._doc) {
        doc = " - " + parameterTestCase._doc;
    }
    const testFn = () => {
        const result = validate(parameterTestCase, parameterModelsForFile(file));
        expect(result).toBe(null);
    };
    if (SKIP_TEST_FILES.has(file)) {
        it.skip("should validate example parameter request (from parameter_spec.yml)" + doc, testFn);
    } else {
        it("should validate example parameter request (from parameter_spec.yml)" + doc, testFn);
    }
}

function itShouldInvalidateParameter(file: string, index: number, parameterTestCase: TestCase) {
    let doc = " for file [" + file + "] and invalid parameter combination [" + index + "]";
    if (parameterTestCase._doc) {
        doc = " - " + parameterTestCase._doc;
    }
    const testFn = () => {
        const result = validate(parameterTestCase, parameterModelsForFile(file));
        expect(result).not.toBe(null);
    };
    if (SKIP_TEST_FILES.has(file)) {
        it.skip("should fail validation of example parameter request (from parameter_spec.yml)" + doc, testFn);
    } else {
        it("should fail validation of example parameter request (from parameter_spec.yml)" + doc, testFn);
    }
}

describe("Tool Parameter Specification", () => {
    for (const [file, testCases] of Object.entries(SPEC_TESTS as ParameterSpecification)) {
        if (testCases.request_valid) {
            itShouldValidateParameters(file, testCases.request_valid);
        }
        if (testCases.request_invalid) {
            itShouldInvalidateParameters(file, testCases.request_invalid);
        }
    }
});
