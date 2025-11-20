import type {
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
    DataColumnParameterModel,
    DataParameterModel,
    DirectoryUriParameterModel,
    DrillDownParameterModel,
    FloatParameterModel,
    GenomeBuildParameterModel,
    GroupTagParameterModel,
    HiddenParameterModel,
    IntegerParameterModel,
    RepeatParameterModel,
    SectionParameterModel,
    SelectParameterModel,
    TextParameterModel,
    ToolParameterBundleModel,
} from "./parameterModels";

type StructuredInputs = { [parameterName: string]: any };
type FormInputs = { [parameterName: string]: any };

export type ToolParameterModel = ToolParameterBundleModel["parameters"][number];

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

function isGxGenomebuild(model: ToolParameterModel): model is GenomeBuildParameterModel {
    return model.parameter_type == "gx_genomebuild";
}

function isGxDirectoryUri(model: ToolParameterModel): model is DirectoryUriParameterModel {
    return model.parameter_type == "gx_directory_uri";
}

function isGxSection(model: ToolParameterModel): model is SectionParameterModel {
    return model.parameter_type == "gx_section";
}

function isGxGroupTag(model: ToolParameterModel): model is GroupTagParameterModel {
    return model.parameter_type == "gx_group_tag";
}

function isGxDataColumn(model: ToolParameterModel): model is DataColumnParameterModel {
    return model.parameter_type == "gx_data_column";
}

function isGxDrillDown(model: ToolParameterModel): model is DrillDownParameterModel {
    return model.parameter_type == "gx_drill_down";
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

const isUrlDataDict = (v: any) => {
    if (!v || typeof v != "object") {
        return false;
    }
    return "src" in v && "url" in v && v.src === "url" && isString(v.url);
};

const isCollectionDict = (v: any) => {
    if (!v || typeof v != "object") {
        return false;
    }
    return "class" in v && "collection_type" in v && v.class === "Collection";
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
        const integerChecker = (v: any) => {
            if (!Number.isInteger(v)) {
                return false;
            }
            // Check direct min/max on parameter model
            if (parameterModel.min != null && v < parameterModel.min) {
                return false;
            }
            if (parameterModel.max != null && v > parameterModel.max) {
                return false;
            }
            // Check validators if present
            if (parameterModel.validators && parameterModel.validators.length > 0) {
                for (const validator of parameterModel.validators) {
                    if (validator.type === "in_range") {
                        let inRange = true;
                        if (validator.min != null) {
                            if (validator.exclude_min) {
                                inRange = inRange && v > validator.min;
                            } else {
                                inRange = inRange && v >= validator.min;
                            }
                        }
                        if (validator.max != null) {
                            if (validator.exclude_max) {
                                inRange = inRange && v < validator.max;
                            } else {
                                inRange = inRange && v <= validator.max;
                            }
                        }
                        const shouldFail = validator.negate ? inRange : !inRange;
                        if (shouldFail) {
                            return false;
                        }
                    }
                }
            }
            return true;
        };
        checkType = handleOptional(integerChecker, parameterModel);
    } else if (isGxFloat(parameterModel)) {
        const floatChecker = (v: any) => {
            if (!isFloat(v)) {
                return false;
            }
            // Check direct min/max on parameter model
            if (parameterModel.min != null && v < parameterModel.min) {
                return false;
            }
            if (parameterModel.max != null && v > parameterModel.max) {
                return false;
            }
            // Check validators if present
            if (parameterModel.validators && parameterModel.validators.length > 0) {
                for (const validator of parameterModel.validators) {
                    if (validator.type === "in_range") {
                        let inRange = true;
                        if (validator.min != null) {
                            if (validator.exclude_min) {
                                inRange = inRange && v > validator.min;
                            } else {
                                inRange = inRange && v >= validator.min;
                            }
                        }
                        if (validator.max != null) {
                            if (validator.exclude_max) {
                                inRange = inRange && v < validator.max;
                            } else {
                                inRange = inRange && v <= validator.max;
                            }
                        }
                        const shouldFail = validator.negate ? inRange : !inRange;
                        if (shouldFail) {
                            return false;
                        }
                    }
                }
            }
            return true;
        };
        checkType = handleOptional(floatChecker, parameterModel);
    } else if (isGxText(parameterModel)) {
        const textChecker = (v: any) => {
            if (!isString(v)) {
                return false;
            }
            // Check validators if present
            if (parameterModel.validators && parameterModel.validators.length > 0) {
                for (const validator of parameterModel.validators) {
                    if (validator.type === "empty_field") {
                        const isEmpty = v === "";
                        const shouldFail = validator.negate ? !isEmpty : isEmpty;
                        if (shouldFail) {
                            return false;
                        }
                    } else if (validator.type === "regex") {
                        try {
                            const regex = new RegExp(validator.expression);
                            const matches = regex.test(v);
                            const shouldFail = validator.negate ? matches : !matches;
                            if (shouldFail) {
                                return false;
                            }
                        } catch (e) {
                            // Invalid regex, skip this validator
                        }
                    } else if (validator.type === "length") {
                        const length = v.length;
                        let shouldFail = false;
                        if (validator.min != null && length < validator.min) {
                            shouldFail = true;
                        }
                        if (validator.max != null && length > validator.max) {
                            shouldFail = true;
                        }
                        if (validator.negate) {
                            shouldFail = !shouldFail;
                        }
                        if (shouldFail) {
                            return false;
                        }
                    }
                    // expression validator skipped - would require Python evaluation
                }
            }
            return true;
        };
        checkType = handleOptional(textChecker, parameterModel);
    } else if (isGxBoolean(parameterModel)) {
        checkType = handleOptional(isBool, parameterModel);
    } else if (isGxHidden(parameterModel)) {
        const hiddenChecker = (v: any) => {
            if (!isString(v)) {
                return false;
            }
            // Check validators if present (similar to text parameters)
            if (parameterModel.validators && parameterModel.validators.length > 0) {
                for (const validator of parameterModel.validators) {
                    if (validator.type === "empty_field") {
                        const isEmpty = v === "";
                        const shouldFail = validator.negate ? !isEmpty : isEmpty;
                        if (shouldFail) {
                            return false;
                        }
                    } else if (validator.type === "regex") {
                        try {
                            const regex = new RegExp(validator.expression);
                            const matches = regex.test(v);
                            const shouldFail = validator.negate ? matches : !matches;
                            if (shouldFail) {
                                return false;
                            }
                        } catch (e) {
                            // Invalid regex, skip this validator
                        }
                    } else if (validator.type === "expression") {
                        // Handle simple Python expressions that can be evaluated in JS
                        // Pattern: 'substring' in value or '''substring''' in value
                        const inMatch = validator.expression.match(/^['"]{1,3}([^'"]+)['"]{1,3}\s+in\s+value$/);
                        if (inMatch && inMatch[1]) {
                            const substring = inMatch[1];
                            const contains = v.includes(substring);
                            const shouldFail = validator.negate ? contains : !contains;
                            if (shouldFail) {
                                return false;
                            }
                        } else if (
                            validator.expression &&
                            (/^[\^$.*+?()[\]{}|\\-]/.test(validator.expression) ||
                                validator.expression.includes(".*") ||
                                validator.expression.endsWith("$"))
                        ) {
                            // Try to treat as regex if it looks like a regex pattern
                            try {
                                const regex = new RegExp(validator.expression);
                                const matches = regex.test(v);
                                const shouldFail = validator.negate ? matches : !matches;
                                if (shouldFail) {
                                    return false;
                                }
                            } catch (e) {
                                // Not a valid regex, skip this validator
                            }
                        }
                        // For other expression validators, we can't evaluate Python expressions in JS
                        // So we skip them
                    } else if (validator.type === "length") {
                        const length = v.length;
                        let shouldFail = false;
                        if (validator.min != null && length < validator.min) {
                            shouldFail = true;
                        }
                        if (validator.max != null && length > validator.max) {
                            shouldFail = true;
                        }
                        if (validator.negate) {
                            shouldFail = !shouldFail;
                        }
                        if (shouldFail) {
                            return false;
                        }
                    }
                }
            }
            return true;
        };
        checkType = handleOptional(hiddenChecker, parameterModel);
    } else if (isGxColor(parameterModel)) {
        const isColorString = (v: any) => {
            return isString(v) && /^#[0-9A-F]{6}$/i.test(v);
        };
        checkType = handleOptional(isColorString, parameterModel);
    } else if (isGxData(parameterModel)) {
        const isMultiDataDict = (v: any) => {
            return isSrcReferenceObject(v, ["hda", "ldda", "hdca"]);
        };
        const isDataItem = (v: any) => {
            // Can be standard data dict (hda/ldda) or URL format
            return isDataDict(v) || isUrlDataDict(v);
        };
        const isMultiDataItem = (v: any) => {
            // For multiple, can also accept hdca
            return isMultiDataDict(v) || isUrlDataDict(v);
        };
        const isArrayOfDataDict = (v: any) => {
            return isArrayOf(v, isMultiDataItem);
        };
        const isBatchData = (v: any) => {
            return isBatch(v, isMultiDataItem);
        };
        let checkRaw: TypeChecker;
        if (parameterModel.multiple) {
            checkRaw = handleOptional((v) => {
                return isMultiDataItem(v) || isArrayOfDataDict(v);
            }, parameterModel);
        } else {
            checkRaw = isDataItem;
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
            // Multiple select can accept null or array of strings
            checkType = (v: any) => {
                if (v === null) {
                    return true;
                }
                return isArrayOf(v, isElement);
            };
        } else {
            checkType = isElement;
        }
        checkType = handleOptional(checkType, parameterModel);
    } else if (isGxDataCollection(parameterModel)) {
        const isDataCollectionDict = (v: any) => {
            // Can be standard hdca reference or Collection object
            return isSrcReferenceObject(v, ["hdca"]) || isCollectionDict(v);
        };
        checkType = handleOptional(isDataCollectionDict, parameterModel);
    } else if (isGxDataColumn(parameterModel)) {
        // Data column parameters are integers (or arrays of integers if multiple)
        const dataColumnChecker = (v: any) => {
            if (!Number.isInteger(v)) {
                return false;
            }
            return true;
        };
        if (parameterModel.multiple) {
            // Multiple data column accepts array of integers
            checkType = (v: any) => {
                return isArrayOf(v, dataColumnChecker);
            };
        } else {
            // Single data column must be an integer (not string, not array)
            checkType = dataColumnChecker;
        }
        checkType = handleOptional(checkType, parameterModel);
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
    } else if (isGxGenomebuild(parameterModel)) {
        const genomebuildChecker = (v: any) => {
            if (!isString(v)) {
                return false;
            }
            return true;
        };
        if (parameterModel.multiple) {
            // Multiple genomebuild can accept null or array of strings
            checkType = (v: any) => {
                if (v === null) {
                    return true;
                }
                return isArrayOf(v, genomebuildChecker);
            };
        } else {
            checkType = handleOptional(genomebuildChecker, parameterModel);
        }
    } else if (isGxDirectoryUri(parameterModel)) {
        const directoryUriChecker = (v: any) => {
            if (!isString(v)) {
                return false;
            }
            // Directory URIs must be valid URIs (have a scheme:// format)
            // Valid schemes include: gxfiles://, http://, https://, ftp://, file://, etc.
            // Check for URI format: scheme://path
            const uriPattern = /^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//;
            if (!uriPattern.test(v)) {
                return false;
            }
            // Check validators if present (similar to text parameters)
            if (parameterModel.validators && parameterModel.validators.length > 0) {
                for (const validator of parameterModel.validators) {
                    if (validator.type === "empty_field") {
                        const isEmpty = v === "";
                        const shouldFail = validator.negate ? !isEmpty : isEmpty;
                        if (shouldFail) {
                            return false;
                        }
                    } else if (validator.type === "regex") {
                        try {
                            const regex = new RegExp(validator.expression);
                            const matches = regex.test(v);
                            const shouldFail = validator.negate ? matches : !matches;
                            if (shouldFail) {
                                return false;
                            }
                        } catch (e) {
                            // Invalid regex, skip this validator
                        }
                    } else if (validator.type === "expression") {
                        // Handle simple Python expressions that can be evaluated in JS
                        // Pattern: 'substring' in value or '''substring''' in value
                        const inMatch = validator.expression.match(/^['"]{1,3}([^'"]+)['"]{1,3}\s+in\s+value$/);
                        if (inMatch && inMatch[1]) {
                            const substring = inMatch[1];
                            const contains = v.includes(substring);
                            const shouldFail = validator.negate ? contains : !contains;
                            if (shouldFail) {
                                return false;
                            }
                        } else if (
                            validator.expression &&
                            (/^[\^$.*+?()[\]{}|\\-]/.test(validator.expression) ||
                                validator.expression.includes(".*") ||
                                validator.expression.endsWith("$"))
                        ) {
                            // Try to treat as regex if it looks like a regex pattern
                            try {
                                const regex = new RegExp(validator.expression);
                                const matches = regex.test(v);
                                const shouldFail = validator.negate ? matches : !matches;
                                if (shouldFail) {
                                    return false;
                                }
                            } catch (e) {
                                // Not a valid regex, skip this validator
                            }
                        }
                        // For other expression validators, we can't evaluate Python expressions in JS
                        // So we skip them
                    } else if (validator.type === "length") {
                        const length = v.length;
                        let shouldFail = false;
                        if (validator.min != null && length < validator.min) {
                            shouldFail = true;
                        }
                        if (validator.max != null && length > validator.max) {
                            shouldFail = true;
                        }
                        if (validator.negate) {
                            shouldFail = !shouldFail;
                        }
                        if (shouldFail) {
                            return false;
                        }
                    }
                }
            }
            return true;
        };
        checkType = handleOptional(directoryUriChecker, parameterModel);
    } else if (isGxRepeat(parameterModel)) {
        if (!Array.isArray(inputValue)) {
            results.push(`Parameter ${inputKey} is not an array of values.`);
        } else {
            // Check min/max constraints
            if (parameterModel.min != null && inputValue.length < parameterModel.min) {
                results.push(`Parameter ${inputKey} must have at least ${parameterModel.min} repeat instances.`);
            }
            if (parameterModel.max != null && inputValue.length > parameterModel.max) {
                results.push(`Parameter ${inputKey} must have at most ${parameterModel.max} repeat instances.`);
            }
            // Validate each repeat instance
            for (const inputs of inputValue) {
                const instanceResults = validateParameters(inputs, parameterModel.parameters);
                extendValidationResults(results, instanceResults);
            }
        }
    } else if (isGxConditional(parameterModel)) {
        const testParameter = parameterModel.test_parameter;
        const whens = parameterModel.whens;
        const testParameterName = testParameter.name;
        let testParameterValue = inputValue[testParameterName];

        // Determine effective test parameter value (use default if missing)
        if (testParameterValue === undefined || testParameterValue === null) {
            // Use default value from test parameter if available
            if ("value" in testParameter && testParameter.value !== null && testParameter.value !== undefined) {
                testParameterValue = testParameter.value;
            }
        }

        // Find matching "when" clause
        let matchingWhen = null;
        if (testParameterValue === null || testParameterValue === undefined) {
            // Look for default_when
            for (const when of whens) {
                if (when.is_default_when) {
                    matchingWhen = when;
                    break;
                }
            }
        } else {
            // Look for matching discriminator
            for (const when of whens) {
                if (when.discriminator === testParameterValue) {
                    matchingWhen = when;
                    break;
                }
            }
            // If no match found and test parameter has default, try default_when
            if (!matchingWhen && "value" in testParameter && testParameter.value !== null) {
                for (const when of whens) {
                    if (when.is_default_when) {
                        matchingWhen = when;
                        break;
                    }
                }
            }
        }

        if (matchingWhen) {
            // Validate only parameters from the matching "when" branch
            const whenParameters = matchingWhen.parameters.concat([testParameter]);
            const whenResults = validateParameters(inputValue, whenParameters);
            extendValidationResults(results, whenResults);

            // Check for parameters from other branches that shouldn't be present
            const allowedParameterNames = new Set<string>();
            whenParameters.forEach((p) => allowedParameterNames.add(p.name));
            for (const when of whens) {
                if (when !== matchingWhen) {
                    for (const param of when.parameters) {
                        if (param.name in inputValue && !allowedParameterNames.has(param.name)) {
                            results.push(`Parameter ${param.name} is not valid for the selected conditional branch.`);
                        }
                    }
                }
            }
        } else {
            // No matching when clause found
            if (testParameterValue === null || testParameterValue === undefined) {
                // Check if test parameter is optional or has default
                const hasDefault =
                    "value" in testParameter && testParameter.value !== null && testParameter.value !== undefined;
                if (!testParameter.optional && !hasDefault) {
                    results.push(
                        `Non optional conditional test parameter ${testParameterName} was not found in inputs.`,
                    );
                }
            } else {
                results.push(
                    `Invalid conditional test value (${testParameterValue}) for parameter (${testParameterName}).`,
                );
            }
        }
    } else if (isGxSection(parameterModel)) {
        // Section parameters contain nested child parameters
        // Validate the child parameters within the section
        if (typeof inputValue != "object" || inputValue === null || Array.isArray(inputValue)) {
            results.push(`Parameter ${inputKey} must be an object.`);
        } else {
            const sectionResults = validateParameters(inputValue, parameterModel.parameters);
            extendValidationResults(results, sectionResults);
        }
    } else if (isGxGroupTag(parameterModel)) {
        // Group tag parameters are strings (or arrays of strings if multiple)
        const groupTagChecker = (v: any) => {
            if (!isString(v)) {
                return false;
            }
            return true;
        };
        if (parameterModel.multiple) {
            // Multiple group tag accepts array of strings
            // null is only allowed if optional
            checkType = (v: any) => {
                if (v === null) {
                    // null is only valid if parameter is optional
                    return parameterModel.optional === true;
                }
                return isArrayOf(v, groupTagChecker);
            };
        } else {
            checkType = groupTagChecker;
        }
        checkType = handleOptional(checkType, parameterModel);
    } else if (isGxDrillDown(parameterModel)) {
        // Drill down parameters are strings (or arrays of strings if multiple)
        // If options are provided, validate against possible values
        const drillDownChecker = (v: any) => {
            if (!isString(v)) {
                return false;
            }
            // If options are provided, check if value is valid
            if (parameterModel.options && parameterModel.options.length > 0) {
                // Extract all possible values from the options tree
                // Logic matches Python: drill_down_possible_values
                // - For exact hierarchy: all nodes are selectable
                // - For recurse hierarchy with multiple=True: all nodes are selectable
                // - For recurse hierarchy with multiple=False: only leaf nodes are selectable
                const possibleValues = new Set<string>();
                const extractValues = (options: any[], hierarchy: string, multiple: boolean) => {
                    for (const option of options) {
                        const isLeaf = !option.options || option.options.length === 0;
                        // Skip only if: not multiple AND not leaf AND recurse hierarchy
                        if (!(hierarchy === "recurse" && !multiple && !isLeaf)) {
                            if (option.value) {
                                possibleValues.add(option.value);
                            }
                        }
                        if (option.options && option.options.length > 0) {
                            extractValues(option.options, hierarchy, multiple);
                        }
                    }
                };
                extractValues(parameterModel.options, parameterModel.hierarchy, parameterModel.multiple);
                if (!possibleValues.has(v)) {
                    return false;
                }
            }
            return true;
        };
        if (parameterModel.multiple) {
            // Multiple drill down accepts array of strings
            checkType = (v: any) => {
                return isArrayOf(v, drillDownChecker);
            };
        } else {
            checkType = drillDownChecker;
        }
        checkType = handleOptional(checkType, parameterModel);
    }
    if (checkType && !checkType(inputValue)) {
        results.push(`Parameter ${inputKey} is of invalid type.`);
    }
    return results;
}

function validateParameters(
    structuredInputs: StructuredInputs,
    parameterModels: Array<ToolParameterModel>,
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
        // Check for default value (value field or default_value field)
        if (
            toolInput &&
            (("value" in toolInput && toolInput.value !== null && toolInput.value !== undefined) ||
                ("default_value" in toolInput &&
                    toolInput.default_value !== null &&
                    toolInput.default_value !== undefined))
        ) {
            continue;
        }
        if (isGxConditional(parameterModel)) {
            continue;
        }
        // GenomeBuild parameters don't require a value in requests (they have implicit defaults)
        if (isGxGenomebuild(parameterModel)) {
            continue;
        }
        // Select parameters don't require a value in requests (API will use first static option)
        if (isGxSelect(parameterModel)) {
            continue;
        }
        // Repeat parameters can be skipped entirely if min is 0 or None, OR if all child parameters are optional/have defaults
        if (isGxRepeat(parameterModel)) {
            // Check if repeat requires a value (min > 0 AND at least one child parameter requires a value)
            let repeatRequiresValue = false;
            if (parameterModel.min != null && parameterModel.min > 0) {
                // Check if any child parameter requires a value
                for (const childParam of parameterModel.parameters) {
                    const isOptional = "optional" in childParam && childParam.optional === true;
                    const hasDefaultValue =
                        ("value" in childParam && childParam.value !== null && childParam.value !== undefined) ||
                        ("default_value" in childParam &&
                            childParam.default_value !== null &&
                            childParam.default_value !== undefined);
                    const childRequiresValue = !isOptional && !hasDefaultValue;
                    if (childRequiresValue) {
                        repeatRequiresValue = true;
                        break;
                    }
                }
            }
            if (!repeatRequiresValue) {
                continue;
            }
        }
        // Section parameters can be skipped entirely if all child parameters are optional/have defaults
        if (isGxSection(parameterModel)) {
            // Check if any child parameter requires a value
            let sectionRequiresValue = false;
            for (const childParam of parameterModel.parameters) {
                const isOptional = "optional" in childParam && childParam.optional === true;
                const hasDefaultValue =
                    ("value" in childParam && childParam.value !== null && childParam.value !== undefined) ||
                    ("default_value" in childParam &&
                        childParam.default_value !== null &&
                        childParam.default_value !== undefined);
                const childRequiresValue = !isOptional && !hasDefaultValue;
                if (childRequiresValue) {
                    sectionRequiresValue = true;
                    break;
                }
            }
            if (!sectionRequiresValue) {
                continue;
            }
        }
        results.push(`Non optional parameter ${inputKey} was not found in inputs.`);
    }
    return results;
}

export function validate(structuredInputs: object, toolInputs: Array<ToolParameterModel>) {
    const results = validateParameters(structuredInputs, toolInputs);
    return results.length == 0 ? null : results;
}
