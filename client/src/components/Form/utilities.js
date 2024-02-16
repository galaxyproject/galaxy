import _ from "underscore";

/** Visits tool inputs.
 * @param{dict}   inputs    - Nested dictionary of input elements
 * @param{dict}   callback  - Called with the mapped dictionary object and corresponding model node
 */
export function visitInputs(inputs, callback, prefix, context) {
    context = Object.assign({}, context);
    _.each(inputs, (input) => {
        if (input && input.type && input.name) {
            context[input.name] = input;
        }
    });
    for (var key in inputs) {
        var node = inputs[key];
        node.name = node.name || key;
        var name = prefix ? `${prefix}|${node.name}` : node.name;
        switch (node.type) {
            case "repeat":
                _.each(node.cache, (cache, j) => {
                    visitInputs(cache, callback, `${name}_${j}`, context);
                });
                break;
            case "conditional":
                if (node.test_param) {
                    callback(node.test_param, `${name}|${node.test_param.name}`, context);
                    var selectedCase = matchCase(node, node.test_param.value);
                    if (selectedCase != -1) {
                        visitInputs(node.cases[selectedCase].inputs, callback, name, context);
                    } else {
                        console.debug(`Form.utilities::visitInputs() - Invalid case for ${name}.`);
                    }
                } else {
                    console.debug(`Form.utilities::visitInputs() - Conditional test parameter missing for ${name}.`);
                }
                break;
            case "section":
                visitInputs(node.inputs, callback, name, context);
                break;
            default:
                callback(node, name, context);
        }
    }
}

/** Matches conditional values to selected cases.
 * @param{dict}   input     - Definition of conditional input parameter
 * @param{dict}   value     - Current value
 */
export function matchCase(input, value) {
    if (input.test_param.type == "boolean") {
        if (["true", true].includes(value)) {
            if (input.test_param.truevalue !== undefined) {
                value = input.test_param.truevalue;
            } else {
                value = "true";
            }
        } else {
            if (input.test_param.falsevalue !== undefined) {
                value = input.test_param.falsevalue;
            } else {
                value = "false";
            }
        }
    }
    for (let i = 0; i < input.cases.length; i++) {
        if (input.cases[i].value == value) {
            return i;
        }
    }
    return -1;
}

/** Match server validation response to highlight inputs
 * @param{dict}   index     - Index of input elements
 * @param{dict}   response  - Nested dictionary with error/warning messages
 */
export function matchInputs(index, response) {
    var result = {};
    function search(id, head) {
        if (typeof head === "string") {
            if (index[id]) {
                result[id] = head;
            }
        } else {
            for (var i in head) {
                var new_id = i;
                if (id !== "") {
                    var separator = "|";
                    if (head instanceof Array) {
                        separator = "_";
                    }
                    new_id = id + separator + new_id;
                }
                search(new_id, head[i]);
            }
        }
    }
    search("", response);
    return result;
}

/** Validates input parameters to identify issues before submitting a server request, where comprehensive validation is performed.
 * @param{dict}   index     - Index of input elements
 * @param{dict}   values    - Dictionary of parameter values
 */
export function validateInputs(index, values, allowEmptyValueOnRequiredInput = false) {
    let batchN = -1;
    let batchSrc = null;
    for (const inputId in values) {
        const inputValue = values[inputId];
        const inputDef = index[inputId];
        if (!inputDef || inputDef.step_linked) {
            continue;
        }
        if (!inputDef.optional && inputDef.type != "hidden") {
            if (inputValue == null || (allowEmptyValueOnRequiredInput && inputValue === "")) {
                return [inputId, "Please provide a value for this option."];
            }
        }
        if (inputDef.wp_linked && inputDef.text_value == inputValue) {
            return [inputId, "Please provide a value for this workflow parameter."];
        }
        if (inputValue && Array.isArray(inputValue.values) && inputValue.values.length == 0 && !inputDef.optional) {
            return [inputId, "Please provide data for this input."];
        }
        if (inputValue) {
            if (inputValue.rules && inputValue.rules.length == 0) {
                return [inputId, "No rules defined, define at least one rule."];
            }
            if (inputValue.mapping && inputValue.mapping.length == 0) {
                return [inputId, "No collection identifiers defined, specify at least one collection identifier."];
            }
            if (inputValue.rules && inputValue.rules.length > 0) {
                for (const rule of inputValue.rules) {
                    if (rule.error) {
                        return [inputId, "Error detected in one or more rules."];
                    }
                }
            }
        }
        if (inputValue && inputValue.batch) {
            const n = inputValue.values.length;
            const src = n > 0 && inputValue.values[0] && inputValue.values[0].src;
            if (src) {
                if (batchSrc === null) {
                    batchSrc = src;
                } else if (batchSrc !== src) {
                    return [inputId, "Please select either dataset or dataset list fields for all batch mode fields."];
                }
            }
            if (batchN === -1) {
                batchN = n;
            } else if (batchN !== n) {
                return [
                    inputId,
                    `Please make sure that you select the same number of inputs for all batch mode fields. This field contains <b>${n}</b> selection(s) while a previous field contains <b>${batchN}</b>.`,
                ];
            }
        }
    }
    return null;
}
