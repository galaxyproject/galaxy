import { describe, expect, it } from "vitest";
import { ref } from "vue";

import { useFormState } from "./useFormState.ts";

function makeConditionalInputs() {
    return [
        { name: "text_field", type: "text", value: "hello" },
        {
            name: "cond",
            type: "conditional",
            test_param: { name: "sel", type: "select", value: "a" },
            cases: [
                {
                    value: "a",
                    inputs: [{ name: "in_a", type: "text", value: "va" }],
                },
                {
                    value: "b",
                    inputs: [{ name: "in_b", type: "text", value: "vb" }],
                },
            ],
        },
    ];
}

describe("useFormState", () => {
    it("leaves the original inputs unchanged when the cloned value changes", () => {
        const original = makeConditionalInputs();
        const originalJson = JSON.stringify(original);
        const { cloneInputs, formInputs } = useFormState();
        cloneInputs(original);

        formInputs.value[0].value = "mutated";

        expect(JSON.stringify(original)).toEqual(originalJson);
    });

    it("clones frozen inputs and builds their form data", () => {
        const frozen = makeConditionalInputs();
        Object.freeze(frozen);
        frozen.forEach((input) => Object.freeze(input));

        const { cloneInputs, buildFormData } = useFormState();
        expect(() => {
            cloneInputs(frozen);
            buildFormData();
        }).not.toThrow();
    });

    it("syncs server attributes while preserving client values, errors, and warnings", () => {
        const { cloneInputs, formInputs, syncServerAttributes } = useFormState();
        cloneInputs(makeConditionalInputs());

        const textInput = formInputs.value[0];
        const valueBefore = textInput.value;
        const errorBefore = textInput.error;
        const warningBefore = textInput.warning;

        const serverInputs = makeConditionalInputs();
        serverInputs[0].value = "server_value";
        serverInputs[0].options = [["opt1", "opt1"]];
        serverInputs[0].error = "server_error";
        serverInputs[0].warning = "server_warning";

        syncServerAttributes(serverInputs);

        expect(textInput.attributes).toBeDefined();
        expect(textInput.attributes.options).toEqual([["opt1", "opt1"]]);
        expect(textInput.attributes.name).toEqual("text_field");
        expect(textInput.attributes.value).toBeUndefined();
        expect(textInput.attributes.error).toBeUndefined();
        expect(textInput.attributes.warning).toBeUndefined();
        expect(textInput.value).toEqual(valueBefore);
        expect(textInput.error).toEqual(errorBefore);
        expect(textInput.warning).toEqual(warningBefore);
    });

    it("indexes only the active conditional case", () => {
        const { cloneInputs, formIndex, rebuildIndex } = useFormState();
        cloneInputs(makeConditionalInputs());
        rebuildIndex();

        expect(formIndex.value["cond|in_a"]).toBeDefined();
        expect(formIndex.value["cond|in_b"]).toBeUndefined();
        expect(formIndex.value["text_field"]).toBeDefined();
        expect(formIndex.value["cond|sel"]).toBeDefined();
    });

    it("applies errors to active parameters and ignores the inactive case", () => {
        const { cloneInputs, applyErrors, formIndex } = useFormState();
        cloneInputs(makeConditionalInputs());

        applyErrors({
            text_field: "error on text",
            cond: { in_a: "error on a", in_b: "error on b" },
        });

        expect(formIndex.value["text_field"].error).toEqual("error on text");
        expect(formIndex.value["cond|in_a"].error).toEqual("error on a");
        expect(formIndex.value["cond|in_b"]).toBeUndefined();
    });

    it("returns form data without assigning it until the caller does", () => {
        const { cloneInputs, formData, buildFormData } = useFormState();
        cloneInputs(makeConditionalInputs());

        expect(formData.value).toEqual({});

        const result = buildFormData();
        expect(formData.value).toEqual({});
        expect(result).toEqual({
            text_field: "hello",
            "cond|sel": "a",
            "cond|in_a": "va",
        });

        formData.value = result;
        expect(formData.value).toEqual(result);
    });

    it("syncs attributes for both active and inactive conditional cases", () => {
        const { cloneInputs, formInputs, syncServerAttributes } = useFormState();
        cloneInputs(makeConditionalInputs());

        const serverInputs = makeConditionalInputs();
        serverInputs[1].cases[1].inputs[0].options = [["col1", "col1"]];

        syncServerAttributes(serverInputs);

        const condNode = formInputs.value[1];
        const caseAInput = condNode.cases[0].inputs[0];
        const caseBInput = condNode.cases[1].inputs[0];
        expect(caseAInput.attributes).toBeDefined();
        expect(caseBInput.attributes).toBeDefined();
        expect(caseBInput.attributes.options).toEqual([["col1", "col1"]]);
    });

    it("keeps distinct server options for parameters with the same name in different cases", () => {
        const { cloneInputs, formInputs, syncServerAttributes } = useFormState();

        cloneInputs([
            {
                name: "col_choice",
                type: "conditional",
                test_param: { name: "col", type: "select", value: "0" },
                cases: [
                    { value: "0", inputs: [{ name: "feature", type: "select", value: null }] },
                    { value: "2", inputs: [{ name: "feature", type: "select", value: null }] },
                ],
            },
        ]);

        syncServerAttributes([
            {
                name: "col_choice",
                type: "conditional",
                test_param: { name: "col", type: "select" },
                cases: [
                    { value: "0", inputs: [{ name: "feature", type: "select", options: [["seqA", "seqA"]] }] },
                    {
                        value: "2",
                        inputs: [
                            {
                                name: "feature",
                                type: "select",
                                options: [
                                    ["mRNA", "mRNA"],
                                    ["exon", "exon"],
                                ],
                            },
                        ],
                    },
                ],
            },
        ]);

        const conditional = formInputs.value[0];
        const case0Feature = conditional.cases[0].inputs[0];
        const case2Feature = conditional.cases[1].inputs[0];

        expect(case0Feature.attributes.options).toEqual([["seqA", "seqA"]]);
        expect(case2Feature.attributes.options).toEqual([
            ["mRNA", "mRNA"],
            ["exon", "exon"],
        ]);
    });

    it("replaces the active case in the index and form data when the selector changes", () => {
        const { cloneInputs, formInputs, rebuildIndex, buildFormData, formIndex, formData } = useFormState();
        cloneInputs(makeConditionalInputs());
        formData.value = buildFormData();

        expect(formIndex.value["cond|in_a"]).toBeDefined();
        expect(formIndex.value["cond|in_b"]).toBeUndefined();
        expect(formData.value["cond|in_a"]).toEqual("va");

        formInputs.value[1].test_param.value = "b";
        rebuildIndex();
        formData.value = buildFormData();

        expect(formIndex.value["cond|in_a"]).toBeUndefined();
        expect(formIndex.value["cond|in_b"]).toBeDefined();
        expect(formData.value["cond|in_b"]).toEqual("vb");
        expect(formData.value["cond|in_a"]).toBeUndefined();
    });

    it("replaces a value and returns its refresh-on-change setting", () => {
        const { cloneInputs, formIndex, replaceParams } = useFormState();
        const inputs = makeConditionalInputs();
        inputs[0].refresh_on_change = true;
        cloneInputs(inputs);

        const refresh = replaceParams({ text_field: "replaced" });
        expect(formIndex.value["text_field"].value).toEqual("replaced");
        expect(refresh).toBe(true);
    });

    it("changes validation from valid to required when the value becomes null", () => {
        const { cloneInputs, buildFormData, formInputs, rebuildIndex, formData, validation } = useFormState();
        const inputs = [{ name: "required_field", type: "text", value: "has_value" }];
        cloneInputs(inputs);
        formData.value = buildFormData();

        expect(validation.value).toBeNull();

        formInputs.value[0].value = null;
        rebuildIndex();
        formData.value = buildFormData();

        expect(validation.value).toEqual(["required_field", "Please provide a value for this option."]);
    });

    it("allows empty strings when rejection is disabled but still rejects null", () => {
        const reject = ref(true);
        const { cloneInputs, buildFormData, formInputs, rebuildIndex, formData, validation } = useFormState({
            rejectEmptyRequiredInputs: reject,
        });
        const inputs = [{ name: "field", type: "text", value: "" }];
        cloneInputs(inputs);
        formData.value = buildFormData();

        expect(validation.value).toEqual(["field", "Please provide a value for this option."]);

        reject.value = false;
        formInputs.value[0].value = "";
        rebuildIndex();
        formData.value = buildFormData();
        expect(validation.value).toBeNull();

        formInputs.value[0].value = null;
        rebuildIndex();
        formData.value = buildFormData();
        expect(validation.value).toEqual(["field", "Please provide a value for this option."]);
    });

    it("clears stale errors and warnings when cloning an inactive conditional case", () => {
        const { cloneInputs, formInputs } = useFormState();
        const inputs = makeConditionalInputs();
        inputs[1].cases[1].inputs[0].error = "stale error";
        inputs[1].cases[1].inputs[0].warning = "stale warning";
        cloneInputs(inputs);

        const caseBInput = formInputs.value[1].cases[1].inputs[0];
        expect(caseBInput.error).toBeNull();
        expect(caseBInput.warning).toBeNull();
    });

    /**
     * Known debt: replaceParams and client-side default selection (FormSelect,
     * FormData auto-selecting first option when value===null) flow through the
     * same v-model → onChange path as user edits. The system does not distinguish
     * "inferred default" from "user intent". This is existing behavior inherited
     * from the Options API implementation.
     */
    it("updates submitted values without recording whether the change was programmatic", () => {
        const { cloneInputs, replaceParams, buildFormData, formData } = useFormState();
        cloneInputs(makeConditionalInputs());
        formData.value = buildFormData();

        const before = { ...formData.value };
        replaceParams({ text_field: "programmatic_value" });
        formData.value = buildFormData();

        expect(formData.value["text_field"]).toEqual("programmatic_value");
        expect(before["text_field"]).toEqual("hello");
    });
});
