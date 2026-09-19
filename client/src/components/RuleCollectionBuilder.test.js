import { describe, expect, it } from "vitest";

import RuleCollectionBuilder, { UI_ONLY_RULE_KEYS } from "./RuleCollectionBuilder.vue";

// A rule and a mapping entry, each polluted with all six UI-only keys plus real DSL keys.
function leakedModel() {
    return {
        rules: [
            {
                type: "add_column_metadata",
                value: "identifier0",
                collapsible_value: { __class__: "RuntimeValue" },
                connectable: true,
                is_workflow: false,
                editing: true,
                error: null,
                warn: "some warning",
            },
        ],
        mapping: [
            {
                type: "list_identifiers",
                columns: [1],
                collapsible_value: { __class__: "RuntimeValue" },
                connectable: true,
                is_workflow: false,
                editing: false,
                error: null,
                warn: null,
            },
        ],
    };
}

// resetSource builds the canonical serialization (ruleSourceJson -> tool_state / saved
// sessions, ruleSource -> view-source + localStorage). Exercise it directly against a
// minimal context to avoid rendering the (unrelated, render-brittle) full component.
const resetSource = RuleCollectionBuilder.methods.resetSource;

describe("RuleCollectionBuilder.resetSource serialization", () => {
    it("strips UI-only keys from the serialized output while leaving the live model intact", () => {
        const model = leakedModel();
        const ctx = {
            rules: model.rules,
            mapping: model.mapping,
            exisistingDatasets: true, // skip extension/genome handling
        };

        resetSource.call(ctx);

        // Serialized object (-> tool_state / saved sessions) carries only DSL keys.
        const serializedRule = ctx.ruleSourceJson.rules[0];
        const serializedMapping = ctx.ruleSourceJson.mapping[0];
        for (const key of UI_ONLY_RULE_KEYS) {
            expect(serializedRule).not.toHaveProperty(key);
            expect(serializedMapping).not.toHaveProperty(key);
        }
        expect(serializedRule).toEqual({ type: "add_column_metadata", value: "identifier0" });
        expect(serializedMapping).toEqual({ type: "list_identifiers", columns: [1] });

        // The string form (-> view-source panel + localStorage) is scrubbed too.
        const parsed = JSON.parse(ctx.ruleSource);
        expect(parsed.rules[0]).toEqual({ type: "add_column_metadata", value: "identifier0" });
        expect(parsed.mapping[0]).toEqual({ type: "list_identifiers", columns: [1] });

        // The live model keeps validation/edit state so the builder UI still renders it.
        expect(ctx.rules[0].warn).toBe("some warning");
        expect(ctx.rules[0].editing).toBe(true);
        expect(ctx.rules[0]).toHaveProperty("collapsible_value");
        expect(ctx.mapping[0]).toHaveProperty("error");
    });
});
