import SPEC_PARAMETERS from "./parameter_models.yml";
import SPEC_TESTS from "./parameter_specification.yml";
import { TextParameterModel, ToolParameterModel } from "./parameterModels";
import { structuredInputs, validate } from "./structured";

describe("structured.js", () => {
    it("should parse galaxy integer parameters", () => {
        expect(true).toBe(true);
        const si = structuredInputs({ parameter: "5" }, [
            { name: "parameter", parameter_type: "gx_integer", optional: false },
        ]);
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
    const parameterModel = SPEC_PARAMETERS[filename];
    const parameterObject: ToolParameterModel = parameterModel as TextParameterModel;
    const inputs = [parameterObject];
    return inputs;
}

function itShouldValidateParameter(file: string, index: number, parameterTestCase: TestCase) {
    let doc = " for file [" + file + "] and valid parameter combination [" + index + "]";
    if (parameterTestCase._doc) {
        doc = " - " + parameterTestCase._doc;
    }
    it("should validate example parameter request (from parameter_spec.yml)" + doc, () => {
        const result = validate(parameterTestCase, parameterModelsForFile(file));
        expect(result).toBe(null);
    });
}

function itShouldInvalidateParameter(file: string, index: number, parameterTestCase: TestCase) {
    let doc = " for file [" + file + "] and invalid parameter combination [" + index + "]";
    if (parameterTestCase._doc) {
        doc = " - " + parameterTestCase._doc;
    }
    it("should fail validation of example parameter request (from parameter_spec.yml)" + doc, () => {
        const result = validate(parameterTestCase, parameterModelsForFile(file));
        expect(result).not.toBe(null);
    });
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
