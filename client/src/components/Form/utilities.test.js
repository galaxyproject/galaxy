import { visitInputs, validateInputs, matchCase, matchErrors } from "./utilities";
import toolModel from "./test-data/tool";

function visitInputsString(inputs) {
    let results = "";
    visitInputs(inputs, (input, identifier) => {
        results += `${identifier}=${input.value};`;
    });
    return results;
}

describe("form component utilities", () => {
    it("tool model test", () => {
        const visits = [];
        visitInputs(toolModel.inputs, function (node, name) {
            visits.push({ name: name, node: node });
        });
        const result =
            '[{"name":"a","node":{"name":"a","type":"text"}},{"name":"b|c","node":{"name":"c","type":"select","value":"h","options":[["d","d",false],["h","h",false]]}},{"name":"b|i","node":{"name":"i","type":"text","value":"i"}},{"name":"b|j","node":{"name":"j","type":"text","value":"j"}},{"name":"k_0|l","node":{"name":"l","type":"text","value":"l"}},{"name":"k_0|m|n","node":{"name":"n","type":"select","value":"r","options":[["o","o",false],["r","r",false]]}},{"name":"k_0|m|s","node":{"name":"s","type":"text","value":"s"}},{"name":"k_0|m|t","node":{"name":"t","type":"text","value":"t"}}]';
        expect(JSON.stringify(visits)).toEqual(result);
    });
    it("conditional case matching", () => {
        const input = {
            name: "a",
            type: "conditional",
            test_param: {
                name: "b",
                type: "boolean",
                value: "true",
                truevalue: undefined,
                falsevalue: undefined,
            },
            cases: [
                {
                    value: "true",
                    inputs: [
                        {
                            name: "c",
                            type: "text",
                            value: "cvalue",
                        },
                    ],
                },
                {
                    value: "false",
                    inputs: [
                        {
                            name: "d",
                            type: "text",
                            value: "dvalue",
                        },
                    ],
                },
            ],
        };

        // test simple case matching
        expect(matchCase(input, "true")).toEqual(0);
        expect(matchCase(input, true)).toEqual(0);
        expect(matchCase(input, "false")).toEqual(1);
        expect(matchCase(input, false)).toEqual(1);

        // test truevalue
        input.test_param.truevalue = "truevalue";
        expect(matchCase(input, "true")).toEqual(-1);
        input.cases[0].value = "truevalue";
        expect(matchCase(input, "true")).toEqual(0);

        // test falsevalue
        input.test_param.falsevalue = "falsevalue";
        expect(matchCase(input, "true")).toEqual(0);
        expect(matchCase(input, "false")).toEqual(-1);
        input.cases[1].value = "falsevalue";
        expect(matchCase(input, "false")).toEqual(1);

        // test (empty) truevalue
        input.test_param.truevalue = undefined;
        input.cases[0].value = "true";
        expect(matchCase(input, "true")).toEqual(0);
        input.test_param.truevalue = "";
        expect(matchCase(input, "true")).toEqual(-1);
        input.cases[0].value = "";
        expect(matchCase(input, "true")).toEqual(0);

        // test visit inputs
        expect(visitInputsString([input])).toEqual("a|b=true;a|c=cvalue;");
        input.test_param.value = "false";
        expect(visitInputsString([input])).toEqual("a|b=false;a|d=dvalue;");

        // switch test parameter to other type than boolean e.g. select
        input.test_param.type = "select";
        expect(matchCase(input, "")).toEqual(0);
        expect(matchCase(input, "unavailable")).toEqual(-1);
        expect(matchCase(input, "falsevalue")).toEqual(1);
    });

    it("test basic value validation", () => {
        const index = {
            input_a: {},
            input_b: {},
            input_c: {},
        };
        const values = {
            input_a: "1",
            input_b: "2",
            input_c: { values: [{ id: 0 }] },
        };
        let result = validateInputs(index, values);
        expect(result).toEqual(null);
        values.input_a = undefined;
        result = validateInputs(index, values);
        expect(JSON.stringify(result)).toEqual('["input_a","Please provide a value for this option."]');
        index.input_a.optional = true;
        result = validateInputs(index, values);
        expect(result).toEqual(null);
        values.input_c.values = [];
        result = validateInputs(index, values);
        expect(JSON.stringify(result)).toEqual('["input_c","Please provide data for this input."]');
    });

    it("test error matching", () => {
        const index = {
            input_a: {},
            input_b_0: {},
            "input_c|input_d": {},
        };
        const values = {
            input_a: "error_a",
            input_b: ["error_b"],
            input_c: { input_d: "error_d" },
        };
        const result = matchErrors(index, values);
        expect(result["input_a"]).toEqual("error_a");
        expect(result["input_b_0"]).toEqual("error_b");
        expect(result["input_c|input_d"]).toEqual("error_d");
    });
});
