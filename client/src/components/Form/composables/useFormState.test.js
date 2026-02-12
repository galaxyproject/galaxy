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
    it("should not affect original inputs when mutating clone", () => {
        const original = makeConditionalInputs();
        const originalJson = JSON.stringify(original);
        const { cloneInputs, formInputs } = useFormState();
        cloneInputs(original);

        // Mutate clone
        formInputs.value[0].value = "mutated";

        // Original unchanged
        expect(JSON.stringify(original)).toEqual(originalJson);
    });

    it("should not throw when cloning frozen inputs", () => {
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

    it("should only copy server-owned fields in syncServerAttributes", () => {
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

    it("should contain only active params in formIndex", () => {
        const { cloneInputs, formIndex, rebuildIndex } = useFormState();
        cloneInputs(makeConditionalInputs());
        rebuildIndex();

        // Active case is "a", so in_a is present but in_b is not
        expect(formIndex.value["cond|in_a"]).toBeDefined();
        expect(formIndex.value["cond|in_b"]).toBeUndefined();
        expect(formIndex.value["text_field"]).toBeDefined();
        expect(formIndex.value["cond|sel"]).toBeDefined();
    });

    it("should apply errors only to active params", () => {
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

    it("should compute formData purely from formIndex without side effects", () => {
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

    it("should patch all conditional cases in syncServerAttributes", () => {
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

    it("should update formIndex and formData on conditional switch", () => {
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

    it("should update values and return refreshOnChange from replaceParams", () => {
        const { cloneInputs, formIndex, replaceParams } = useFormState();
        const inputs = makeConditionalInputs();
        inputs[0].refresh_on_change = true;
        cloneInputs(inputs);

        const refresh = replaceParams({ text_field: "replaced" });
        expect(formIndex.value["text_field"].value).toEqual("replaced");
        expect(refresh).toBe(true);
    });

    it("should react to formData changes in validation computed", () => {
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

    it("should respect the rejectEmptyRequiredInputs option", () => {
        const reject = ref(true);
        const { cloneInputs, buildFormData, formInputs, rebuildIndex, formData, validation } = useFormState({
            rejectEmptyRequiredInputs: reject,
        });
        const inputs = [{ name: "field", type: "text", value: "" }];
        cloneInputs(inputs);
        formData.value = buildFormData();

        // With reject=true, empty string on required field triggers error
        expect(validation.value).toEqual(["field", "Please provide a value for this option."]);

        // With reject=false, empty string passes validation
        reject.value = false;
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

    it("should clear errors and warnings on all cases including inactive when cloning", () => {
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
    it("should not distinguish replaceParams from user edits (known debt)", () => {
        const { cloneInputs, replaceParams, buildFormData, formData } = useFormState();
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
