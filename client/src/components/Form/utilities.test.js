import { matchCase, visitInputs } from "./utilities";

function visitInputsString(inputs) {
    let results = "";
    visitInputs(inputs, (input, identifier) => {
        results += `${identifier}-${input.name}&`;
    });
    return results;
}

describe("form component utilities", () => {
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
                    name: "c",
                    value: "true",
                    inputs: [
                        {
                            name: "d",
                            type: "text",
                            value: "d",
                        },
                    ],
                },
                {
                    name: "e",
                    value: "false",
                    inputs: [
                        {
                            name: "f",
                            type: "text",
                            value: "f",
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
        input.test_param.truevalue = "";
        expect(matchCase(input, "true")).toEqual(-1);
        input.cases[0].value = "";
        expect(matchCase(input, "true")).toEqual(0);

        // test visit inputs
        expect(visitInputsString([input])).toEqual("a|b-b&a|d-d&");
        input.test_param.value = "false";
        expect(visitInputsString([input])).toEqual("a|b-b&a|f-f&");

        // switch test parameter to other type than boolean e.g. select
        input.test_param.type = "select";
        expect(matchCase(input, "")).toEqual(0);
        expect(matchCase(input, "unavailable")).toEqual(-1);
    });
});
