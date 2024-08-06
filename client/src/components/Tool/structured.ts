import {
    BooleanParameterModel,
    ColorParameterModel,
    ConditionalParameterModel,
    CwlBooleanParameterModel,
    CwlDirectoryParameterModel,
    CwlFileParameterModel,
    CwlFloatParameterModel,
    CwlIntegerParameterModel,
    CwlNullParameterModel,
    CwlStringParameterModel,
    CwlUnionParameterModel,
    DataCollectionParameterModel,
    DataParameterModel,
    FloatParameterModel,
    HiddenParameterModel,
    IntegerParameterModel,
    RepeatParameterModel,
    SelectParameterModel,
    TextParameterModel,
    ToolParameterModel,
} from "./parameterModels";

type StructuredInputs = { [parameterName: string]: any };
type FormInputs = { [parameterName: string]: any };

export function structuredInputs(formInputs: FormInputs, toolInputs: Array<ToolParameterModel>): StructuredInputs {
    const structuredInputs: StructuredInputs = {};
    for (const toolInput of toolInputs) {
        const inputKey = toolInput.name;
        structuredInputs[inputKey] = parseInt(formInputs[inputKey]);
    }
    const validationResult = validateParameters(structuredInputs, toolInputs);
    if (validationResult.length !== 0) {
        console.log(`Failed structured input validation with... '${validationResult}'`);
        throw Error("Failed parameter validation");
    }
    return structuredInputs;
}

function extendValidationResults(results: Array<string>, withResults: Array<string>) {
    withResults.forEach((obj) => {
        results.push(obj);
    });
}

function isFloat(v: any) {
    return typeof v == "number";
}

function isString(v: any) {
    return typeof v == "string";
}

function isGxInteger(model: ToolParameterModel): model is IntegerParameterModel {
    return model.parameter_type == "gx_integer";
}

function isGxFloat(model: ToolParameterModel): model is FloatParameterModel {
    return model.parameter_type == "gx_float";
}

function isGxText(model: ToolParameterModel): model is TextParameterModel {
    return model.parameter_type == "gx_text";
}

function isGxBoolean(model: ToolParameterModel): model is BooleanParameterModel {
    return model.parameter_type == "gx_boolean";
}

function isGxHidden(model: ToolParameterModel): model is HiddenParameterModel {
    return model.parameter_type == "gx_hidden";
}

function isGxSelect(model: ToolParameterModel): model is SelectParameterModel {
    return model.parameter_type == "gx_select";
}

function isGxColor(model: ToolParameterModel): model is ColorParameterModel {
    return model.parameter_type == "gx_color";
}

function isGxData(model: ToolParameterModel): model is DataParameterModel {
    return model.parameter_type == "gx_data";
}

function isGxDataCollection(model: ToolParameterModel): model is DataCollectionParameterModel {
    return model.parameter_type == "gx_data_collection";
}

function isGxRepeat(model: ToolParameterModel): model is RepeatParameterModel {
    return model.parameter_type == "gx_repeat";
}

function isGxConditional(model: ToolParameterModel): model is ConditionalParameterModel {
    return model.parameter_type == "gx_conditional";
}

function isCwlInteger(model: ToolParameterModel): model is CwlIntegerParameterModel {
    return model.parameter_type == "cwl_integer";
}

function isCwlDirectory(model: ToolParameterModel): model is CwlDirectoryParameterModel {
    return model.parameter_type == "cwl_directory";
}

function isCwlFile(model: ToolParameterModel): model is CwlFileParameterModel {
    return model.parameter_type == "cwl_file";
}

function isCwlUnion(model: ToolParameterModel): model is CwlUnionParameterModel {
    return model.parameter_type == "cwl_union";
}

function isCwlNull(model: ToolParameterModel): model is CwlNullParameterModel {
    return model.parameter_type == "cwl_null";
}

function isCwlBoolean(model: ToolParameterModel): model is CwlBooleanParameterModel {
    return model.parameter_type == "cwl_boolean";
}

function isCwlString(model: ToolParameterModel): model is CwlStringParameterModel {
    return model.parameter_type == "cwl_string";
}

function isCwlFloat(model: ToolParameterModel): model is CwlFloatParameterModel {
    return model.parameter_type == "cwl_float";
}

const isBool = (v: any) => {
    return typeof v == "boolean";
};

function isObjectWithKeys(inputObject: any, requiredKeys: Array<string>): boolean {
    if (!inputObject) {
        return false;
    }
    if (typeof inputObject != "object") {
        return false;
    }
    for (const inputKey of Object.keys(inputObject)) {
        if (requiredKeys.indexOf(inputKey) == -1) {
            return false;
        }
    }
    for (const requiredKey of requiredKeys) {
        if (!(requiredKey in inputObject)) {
            return false;
        }
    }
    return true;
}

function isSrcReferenceObject(v: any, srcTypes: Array<string>) {
    return isObjectWithKeys(v, ["src", "id"]) && srcTypes.indexOf(v.src) >= 0 && isString(v.id);
}

type TypeChecker = (v: any) => boolean;

function isArrayOf(inputObject: any, typeCheck: TypeChecker): boolean {
    if (!Array.isArray(inputObject)) {
        return false;
    }
    for (const el of inputObject) {
        if (!typeCheck(el)) {
            return false;
        }
    }
    return true;
}

const isDataDict = (v: any) => {
    return isSrcReferenceObject(v, ["hda", "ldda"]);
};

const isBatch = (v: any, valueChecker: TypeChecker) => {
    if (!isObjectWithKeys(v, ["__class__", "values"]) || v["__class__"] != "Batch") {
        return false;
    }
    const values = v.values;
    return isArrayOf(values, valueChecker);
};

function simpleCwlTypeChecker(parameterModel: ToolParameterModel) {
    let checkType = null;
    if (isCwlInteger(parameterModel)) {
        checkType = Number.isInteger;
    } else if (isCwlDirectory(parameterModel)) {
        checkType = isDataDict;
    } else if (isCwlFile(parameterModel)) {
        checkType = isDataDict;
    } else if (isCwlNull(parameterModel)) {
        checkType = (v: any) => {
            return v == null;
        };
    } else if (isCwlBoolean(parameterModel)) {
        checkType = isBool;
    } else if (isCwlString(parameterModel)) {
        checkType = isString;
    } else if (isCwlFloat(parameterModel)) {
        checkType = isFloat;
    } else {
        throw Error("Unknown simple CWL type encountered.");
    }
    return checkType;
}

function checkCwlUnionType(parameterModel: CwlUnionParameterModel, inputValue: any) {
    for (const unionedModel of parameterModel.parameters) {
        if (simpleCwlTypeChecker(unionedModel)(inputValue)) {
            return true;
        }
    }
    return false;
}

function validateParameter(inputKey: string, inputValue: any, parameterModel: ToolParameterModel) {
    const results: string[] = [];
    let checkType = null;

    function handleOptional(typeCheck: TypeChecker, parameter: ToolParameterModel) {
        if ("optional" in parameter && parameter.optional) {
            return (v: any) => {
                return v === null || typeCheck(v);
            };
        } else {
            return typeCheck;
        }
    }

    if (isGxInteger(parameterModel)) {
        checkType = handleOptional(Number.isInteger, parameterModel);
    } else if (isGxFloat(parameterModel)) {
        checkType = handleOptional(isFloat, parameterModel);
    } else if (isGxText(parameterModel)) {
        checkType = handleOptional(isString, parameterModel);
    } else if (isGxBoolean(parameterModel)) {
        checkType = handleOptional(isBool, parameterModel);
    } else if (isGxHidden(parameterModel)) {
        checkType = handleOptional(isString, parameterModel);
    } else if (isGxColor(parameterModel)) {
        const isColorString = (v: any) => {
            return isString(v) && /^#[0-9A-F]{6}$/i.test(v);
        };
        checkType = handleOptional(isColorString, parameterModel);
    } else if (isGxData(parameterModel)) {
        const isMultiDataDict = (v: any) => {
            return isSrcReferenceObject(v, ["hda", "ldda", "hdca"]);
        };
        const isArrayOfDataDict = (v: any) => {
            return isArrayOf(v, isMultiDataDict);
        };
        const isBatchData = (v: any) => {
            return isBatch(v, isMultiDataDict);
        };
        let checkRaw: TypeChecker;
        if (parameterModel.multiple) {
            checkRaw = handleOptional((v) => {
                return isMultiDataDict(v) || isArrayOfDataDict(v);
            }, parameterModel);
        } else {
            checkRaw = isDataDict;
        }
        checkType = (v: any) => {
            return checkRaw(v) || isBatchData(v);
        };
        checkType = handleOptional(checkType, parameterModel);
    } else if (isGxSelect(parameterModel)) {
        let isElement: TypeChecker;
        if (parameterModel.options != null) {
            const optionValues = parameterModel.options.map((lv) => {
                return lv.value;
            });
            const isOneOfOptions = (v: any) => {
                return isString(v) && optionValues.indexOf(v) !== -1;
            };
            isElement = isOneOfOptions;
        } else {
            isElement = isString;
        }
        if (parameterModel.multiple) {
            checkType = (v: any) => {
                return isArrayOf(v, isElement);
            };
        } else {
            checkType = isElement;
        }
        checkType = handleOptional(checkType, parameterModel);
    } else if (isGxDataCollection(parameterModel)) {
        const isDataCollectionDict = (v: any) => {
            return isSrcReferenceObject(v, ["hdca"]);
        };
        checkType = handleOptional(isDataCollectionDict, parameterModel);
    } else if (isCwlInteger(parameterModel)) {
        checkType = simpleCwlTypeChecker(parameterModel);
    } else if (isCwlDirectory(parameterModel)) {
        checkType = simpleCwlTypeChecker(parameterModel);
    } else if (isCwlFile(parameterModel)) {
        checkType = simpleCwlTypeChecker(parameterModel);
    } else if (isCwlUnion(parameterModel)) {
        checkType = (v: any) => {
            return checkCwlUnionType(parameterModel, v);
        };
    } else if (isCwlBoolean(parameterModel)) {
        checkType = simpleCwlTypeChecker(parameterModel);
    } else if (isCwlString(parameterModel)) {
        checkType = simpleCwlTypeChecker(parameterModel);
    } else if (isCwlFloat(parameterModel)) {
        checkType = simpleCwlTypeChecker(parameterModel);
    } else if (isGxRepeat(parameterModel)) {
        if (!Array.isArray(inputValue)) {
            results.push(`Parameter ${inputKey} is not an array of values.`);
        } else {
            for (const inputs of inputValue) {
                const instanceResults = validateParameters(inputs, parameterModel.parameters);
                extendValidationResults(results, instanceResults);
            }
        }
    } else if (isGxConditional(parameterModel)) {
        const testParameter = parameterModel.test_parameter;
        let testParameterEffectivelyOptional = testParameter.optional;
        if (!testParameterEffectivelyOptional && "value" in testParameter && testParameter.value !== null) {
            testParameterEffectivelyOptional = true;
        }
        const whens = parameterModel.whens;
        const testParameterName = testParameter.name;
        const testParameterValue = inputValue[testParameterName];
        // validateParameter(testParameterName, testParameterValue, testParameter);
        let testParameterValueFoundInWhen = false;
        for (const when of whens) {
            const inputKey = when.discriminator;
            if (inputKey === testParameterValue) {
                testParameterValueFoundInWhen = true;
                const whenParameters = when.parameters.concat([testParameter]);
                const whenResults = validateParameters(inputValue, whenParameters);
                extendValidationResults(results, whenResults);
                break;
            }
        }
        if (!testParameterValueFoundInWhen && !testParameterEffectivelyOptional) {
            results.push(`Non optional conditional test parameter ${testParameterName} was not found in inputs.`);
        }
    }
    if (checkType && !checkType(inputValue)) {
        results.push(`Parameter ${inputKey} is of invalid type.`);
    }
    return results;
}

function validateParameters(
    structuredInputs: StructuredInputs,
    parameterModels: Array<ToolParameterModel>
): Array<string> {
    const results = [];
    const keysEncountered = [];
    const parameterModelsByName: { [name: string]: ToolParameterModel } = {};
    parameterModels.forEach((v) => {
        parameterModelsByName[v.name] = v;
    });
    for (const inputKey of Object.keys(structuredInputs)) {
        keysEncountered.push(inputKey);
        if (!(inputKey in parameterModelsByName)) {
            results.push(`Unknown parameter ${inputKey} encountered.`);
            continue;
        }
        const inputValue = structuredInputs[inputKey];
        const parameterModel = parameterModelsByName[inputKey];
        if (parameterModel) {
            const parameterResults = validateParameter(inputKey, inputValue, parameterModel);
            extendValidationResults(results, parameterResults);
        }
    }
    for (const parameterModel of parameterModels) {
        const inputKey = parameterModel.name;
        if (keysEncountered.indexOf(inputKey) !== -1) {
            continue;
        }
        const toolInput = parameterModelsByName[inputKey];
        if (toolInput && "optional" in toolInput && toolInput.optional === true) {
            continue;
        }
        if (toolInput && "value" in toolInput && toolInput.value !== null) {
            continue;
        }
        if (isGxConditional(parameterModel)) {
            continue;
        }
        results.push(`Non optional parameter ${inputKey} was not found in inputs.`);
    }
    return results;
}

export function validate(structuredInputs: object, toolInputs: Array<ToolParameterModel>) {
    const results = validateParameters(structuredInputs, toolInputs);
    return results.length == 0 ? null : results;
}
