/** Visits tool inputs
 * @param{dict}   inputs    - Nested dictionary of input elements
 * @param{dict}   callback  - Called with the mapped dictionary object and corresponding model node
 */
export var visitInputs = (inputs, callback, prefix, context) => {
    context = $.extend({}, context);
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
};
