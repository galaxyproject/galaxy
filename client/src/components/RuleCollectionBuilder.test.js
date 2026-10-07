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

// The group-count watcher guards against a count below one. Vue hands a watcher
// (newValue, oldValue), so reading the guard off the wrong parameter clamps on the
// value the field just left rather than the one it just took.
const groupCountWatcher = RuleCollectionBuilder.watch.addColumnRegexGroupCount;

describe("RuleCollectionBuilder add-column-regex group count", () => {
    it("keeps a count typed into a field that was emptied first", () => {
        const ctx = { addColumnRegexGroupCount: "2" };
        groupCountWatcher.call(ctx, "2", "");
        expect(ctx.addColumnRegexGroupCount).toBe("2");
    });

    it("leaves an emptied field alone so the next digit replaces it", () => {
        const ctx = { addColumnRegexGroupCount: "" };
        groupCountWatcher.call(ctx, "", 1);
        expect(ctx.addColumnRegexGroupCount).toBe("");
    });

    it("raises a below-minimum count to one", () => {
        const ctx = { addColumnRegexGroupCount: 0 };
        groupCountWatcher.call(ctx, 0, 2);
        expect(ctx.addColumnRegexGroupCount).toBe(1);
    });
});
