import { describe, expect, it } from "vitest";

import type { SampleSheetColumnDefinition } from "@/api";

import { parseSampleSheetValue } from "./useSampleSheetGrid";

function column(type: SampleSheetColumnDefinition["type"], extra: Partial<SampleSheetColumnDefinition> = {}) {
    return { name: "column", type, optional: false, ...extra } as SampleSheetColumnDefinition;
}

describe("parseSampleSheetValue", () => {
    it.each([
        ["int", "3", 3],
        ["int", 3, 3],
        ["float", "1.5", 1.5],
        ["float", "1e3", 1000],
        ["boolean", "TRUE", true],
        ["boolean", false, false],
        ["string", "treated 1", "treated 1"],
        ["element_identifier", "sample 1", "sample 1"],
    ] as const)("parses a %s column's %j as %j", (type, input, expected) => {
        expect(parseSampleSheetValue(input, column(type))).toEqual({ valid: true, value: expected });
    });

    it.each([
        ["int", "1.5"],
        ["int", ""],
        ["int", null],
        ["float", "1,5"],
        ["float", "1abc"],
        ["boolean", "yes"],
        ["string", "a/b"],
        ["element_identifier", "sample.1"],
    ] as const)("rejects a %s column's %j", (type, input) => {
        expect(parseSampleSheetValue(input, column(type))).toEqual({ valid: false });
    });

    it("clears optional typed columns to null", () => {
        expect(parseSampleSheetValue("", column("float", { optional: true }))).toEqual({ valid: true, value: null });
    });

    it("keeps an optional string column's empty value", () => {
        expect(parseSampleSheetValue("", column("string", { optional: true }))).toEqual({ valid: true, value: "" });
    });

    it("compares restrictions as text", () => {
        const restricted = column("int", { restrictions: [1, 2] });
        expect(parseSampleSheetValue("2", restricted)).toEqual({ valid: true, value: 2 });
        expect(parseSampleSheetValue("3", restricted)).toEqual({ valid: false });
    });
});
