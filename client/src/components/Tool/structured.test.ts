import { structuredInputs, validate } from "./structured";
import { TextParameterModel, ToolParameterModel } from "./parameterModels";

describe("structured.js", () => {
    it("should parse galaxy integer parameters", () => {
        expect(true).toBe(true);
        const si = structuredInputs({ parameter: "5" }, [
            { name: "parameter", parameter_type: "gx_integer", optional: false },
        ]);
        expect(si["parameter"]).toBe(5);
    });
});

import SPEC_PARAMETERS from "./parameter_models.yml";
import SPEC_TESTS from "./parameter_specification.yml";

class FileTestCases {
    request_invalid: Array<any>;
    request_valid: Array<any>;
}

function itShouldValidateParameters(file, parameters) {
    for (const [index, parameter] of parameters.entries()) {
        itShouldValidateParameter(file, index, parameter);
    }
}

function itShouldInvalidateParameters(file, parameters) {
    for (const [index, parameter] of parameters.entries()) {
        itShouldInvalidateParameter(file, index, parameter);
    }
}

function toToolParameterModel(jsonObject): ToolParameterModel {
    const modal: TextParameterModel = jsonObject;
    return modal;
}

function parameterModelsForFile(filename: string): Array<ToolParameterModel> {
    const parameterModel = SPEC_PARAMETERS[filename];
    const parameterObject: ToolParameterModel = toToolParameterModel(parameterModel);
    const inputs = [parameterObject];
    return inputs;
}

function itShouldValidateParameter(file, index, parameterTestCase) {
    let doc = " for file [" + file + "] and valid parameter combination [" + index + "]";
    if (parameterTestCase._doc) {
        doc = " - " + parameterTestCase._doc;
    }
    it("should validate example parameter request (from parameter_spec.yml)" + doc, () => {
        const result = validate(parameterTestCase, parameterModelsForFile(file));
        expect(result).toBe(null);
    });
}

function itShouldInvalidateParameter(file, index, parameterTestCase) {
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
    for (const [file, combos] of Object.entries(SPEC_TESTS)) {
        const testCases: FileTestCases = Object.assign(new FileTestCases(), combos);
        if (testCases.request_valid) {
            itShouldValidateParameters(file, testCases.request_valid);
        }
        if (testCases.request_invalid) {
            itShouldInvalidateParameters(file, testCases.request_invalid);
        }
    }
});
