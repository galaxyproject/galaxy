import { ref } from "vue";
import { describe, expect, it } from "vitest";

import { useFormState } from "./useFormState";

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
    it("I7: clone independence — mutating clone does not affect original", () => {
        const original = makeConditionalInputs();
        const originalJson = JSON.stringify(original);
        const { cloneInputs, formInputs } = useFormState();
        cloneInputs(original);

        // Mutate clone
        formInputs.value[0].value = "mutated";

        // Original unchanged
        expect(JSON.stringify(original)).toEqual(originalJson);
    });

    it("I8: backend response preserved — frozen inputs do not throw", () => {
        const inputs = makeConditionalInputs();
        const frozen = JSON.parse(JSON.stringify(inputs));
        Object.freeze(frozen);
        frozen.forEach((input) => Object.freeze(input));

        const { cloneInputs, buildFormData } = useFormState();
        // cloneInputs does JSON.parse(JSON.stringify(frozen)) — reads frozen, writes to new objects
        expect(() => {
            cloneInputs(frozen);
            buildFormData();
        }).not.toThrow();
    });

    it("I2: syncServerAttributes only copies server-owned fields", () => {
        const { cloneInputs, formInputs, syncServerAttributes } = useFormState();
        cloneInputs(makeConditionalInputs());

        // Snapshot properties before sync
        const textInput = formInputs.value[0];
        const valueBefore = textInput.value;
        const errorBefore = textInput.error;
        const warningBefore = textInput.warning;

        // Create server response with different value, options, and error
        const serverInputs = makeConditionalInputs();
        serverInputs[0].value = "server_value";
        serverInputs[0].options = [["opt1", "opt1"]];
        serverInputs[0].error = "server_error";
        serverInputs[0].warning = "server_warning";

        syncServerAttributes(serverInputs);

        // Server-owned fields are in attributes
        expect(textInput.attributes).toBeDefined();
        expect(textInput.attributes.options).toEqual([["opt1", "opt1"]]);
        expect(textInput.attributes.name).toEqual("text_field");
        // Client-owned fields excluded from attributes
        expect(textInput.attributes.value).toBeUndefined();
        expect(textInput.attributes.error).toBeUndefined();
        expect(textInput.attributes.warning).toBeUndefined();
        // Clone's own properties preserved
        expect(textInput.value).toEqual(valueBefore);
        expect(textInput.error).toEqual(errorBefore);
        expect(textInput.warning).toEqual(warningBefore);
    });

    it("I4: formIndex contains active params only", () => {
        const { cloneInputs, formIndex, rebuildIndex } = useFormState();
        cloneInputs(makeConditionalInputs());
        rebuildIndex();

        // Active case is "a", so in_a is present but in_b is not
        expect(formIndex.value["cond|in_a"]).toBeDefined();
        expect(formIndex.value["cond|in_b"]).toBeUndefined();
        expect(formIndex.value["text_field"]).toBeDefined();
        expect(formIndex.value["cond|sel"]).toBeDefined();
    });

    it("I5: errors apply only to active params", () => {
        const { cloneInputs, applyErrors, formIndex } = useFormState();
        cloneInputs(makeConditionalInputs());

        applyErrors({
            text_field: "error on text",
            cond: { in_a: "error on a", in_b: "error on b" },
        });

        // Active param gets error
        expect(formIndex.value["text_field"].error).toEqual("error on text");
        expect(formIndex.value["cond|in_a"].error).toEqual("error on a");
        // Inactive param "in_b" is not in formIndex, so no error set
        expect(formIndex.value["cond|in_b"]).toBeUndefined();
    });

    it("I3: buildFormData is a pure computation over formIndex", () => {
        const { cloneInputs, formData, buildFormData } = useFormState();
        cloneInputs(makeConditionalInputs());

        // formData starts empty; buildFormData does not mutate it
        expect(formData.value).toEqual({});

        const result = buildFormData();
        // buildFormData returns the params but does not assign formData.value
        expect(formData.value).toEqual({});
        expect(result).toEqual({
            text_field: "hello",
            "cond|sel": "a",
            "cond|in_a": "va",
        });

        // Caller assigns formData.value explicitly
        formData.value = result;
        expect(formData.value).toEqual(result);
    });

    it("syncServerAttributes patches all conditional cases", () => {
        const { cloneInputs, formInputs, syncServerAttributes } = useFormState();
        cloneInputs(makeConditionalInputs());

        // Server response has updated options for inactive case
        const serverInputs = makeConditionalInputs();
        serverInputs[1].cases[1].inputs[0].options = [["col1", "col1"]];

        syncServerAttributes(serverInputs);

        // Both cases should have attributes set
        const condNode = formInputs.value[1];
        const caseAInput = condNode.cases[0].inputs[0];
        const caseBInput = condNode.cases[1].inputs[0];
        expect(caseAInput.attributes).toBeDefined();
        expect(caseBInput.attributes).toBeDefined();
        expect(caseBInput.attributes.options).toEqual([["col1", "col1"]]);
    });

    it("conditional switch updates formIndex and formData", () => {
        const { cloneInputs, formInputs, rebuildIndex, buildFormData, formIndex, formData } = useFormState();
        cloneInputs(makeConditionalInputs());
        formData.value = buildFormData();

        expect(formIndex.value["cond|in_a"]).toBeDefined();
        expect(formIndex.value["cond|in_b"]).toBeUndefined();
        expect(formData.value["cond|in_a"]).toEqual("va");

        // Switch conditional
        formInputs.value[1].test_param.value = "b";
        rebuildIndex();
        formData.value = buildFormData();

        expect(formIndex.value["cond|in_a"]).toBeUndefined();
        expect(formIndex.value["cond|in_b"]).toBeDefined();
        expect(formData.value["cond|in_b"]).toEqual("vb");
        expect(formData.value["cond|in_a"]).toBeUndefined();
    });

    it("replaceParams updates values and returns refreshOnChange", () => {
        const { cloneInputs, formIndex, replaceParams } = useFormState();
        const inputs = makeConditionalInputs();
        inputs[0].refresh_on_change = true;
        cloneInputs(inputs);

        const refresh = replaceParams({ text_field: "replaced" });
        expect(formIndex.value["text_field"].value).toEqual("replaced");
        expect(refresh).toBe(true);
    });

    it("validation computed reacts to formData changes", () => {
        const { cloneInputs, buildFormData, formInputs, rebuildIndex, formData, validation } = useFormState();
        const inputs = [{ name: "required_field", type: "text", value: "has_value" }];
        cloneInputs(inputs);
        formData.value = buildFormData();

        // Valid — has value
        expect(validation.value).toBeNull();

        // Set value to null (required field)
        formInputs.value[0].value = null;
        rebuildIndex();
        formData.value = buildFormData();

        expect(validation.value).toEqual(["required_field", "Please provide a value for this option."]);
    });

    it("allowEmptyValueOnRequiredInput option is respected", () => {
        // allowEmptyValueOnRequiredInput=true means empty string IS treated as invalid
        const allow = ref(true);
        const { cloneInputs, buildFormData, formInputs, rebuildIndex, formData, validation } = useFormState({
            allowEmptyValueOnRequiredInput: allow,
        });
        const inputs = [{ name: "field", type: "text", value: "" }];
        cloneInputs(inputs);
        formData.value = buildFormData();

        // With allow=true, empty string on required field triggers error
        expect(validation.value).toEqual(["field", "Please provide a value for this option."]);

        // With allow=false, empty string passes validation
        allow.value = false;
        formInputs.value[0].value = "";
        rebuildIndex();
        formData.value = buildFormData();
        expect(validation.value).toBeNull();

        // Null always fails regardless of the flag
        formInputs.value[0].value = null;
        rebuildIndex();
        formData.value = buildFormData();
        expect(validation.value).toEqual(["field", "Please provide a value for this option."]);
    });

    it("R6: cloneInputs sets error and warning to null on all cases including inactive", () => {
        const { cloneInputs, formInputs } = useFormState();
        const inputs = makeConditionalInputs();
        // Pre-set errors and warnings on inputs
        inputs[1].cases[1].inputs[0].error = "stale error";
        inputs[1].cases[1].inputs[0].warning = "stale warning";
        cloneInputs(inputs);

        // Both should be cleared even on inactive case
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
    it("known debt: replaceParams is indistinguishable from user edits", () => {
        const { cloneInputs, formIndex, replaceParams, buildFormData, formData } = useFormState();
        cloneInputs(makeConditionalInputs());
        formData.value = buildFormData();

        const before = { ...formData.value };
        replaceParams({ text_field: "programmatic_value" });
        formData.value = buildFormData();

        // The replaced value appears in formData identically to a user edit.
        // There is no metadata distinguishing the source of the change.
        expect(formData.value["text_field"]).toEqual("programmatic_value");
        expect(before["text_field"]).toEqual("hello");
    });
});
