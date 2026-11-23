import { describe, expect, it } from "vitest";

import type { StepInputDefaults } from "@/stores/workflowStepStore";

import { defaultFileLocation, withDefaultFileLocation } from "./defaultFile";

const OLD = "https://example.org/old";
const NEW = "https://example.org/new";

describe("withDefaultFileLocation", () => {
    it.each([
        ["creates a File default", undefined, NEW, { input: { default: { class: "File", location: NEW } } }],
        [
            "keeps format when the location changes",
            { input: { default: { class: "File", location: OLD, format: "tabular" } } },
            NEW,
            { input: { default: { class: "File", location: NEW, format: "tabular" } } },
        ],
        [
            "drops metadata describing the previous file",
            {
                input: {
                    default: { class: "File", location: OLD, format: "tabular", basename: "old.tsv", MD5: "abc" },
                },
            },
            NEW,
            { input: { default: { class: "File", location: NEW, format: "tabular" } } },
        ],
        [
            "keeps metadata when the location is unchanged",
            { input: { default: { class: "File", location: OLD, basename: "old.tsv" } } },
            ` ${OLD} `,
            { input: { default: { class: "File", location: OLD, basename: "old.tsv" } } },
        ],
        ["clears the default", { input: { default: { class: "File", location: OLD } } }, "", {}],
        [
            "keeps other keys of the input when clearing",
            { input: { default: { class: "File", location: OLD }, other: 1 } },
            "",
            { input: { other: 1 } },
        ],
    ])("%s", (_name, stepIn, location, expected) => {
        expect(withDefaultFileLocation(stepIn as StepInputDefaults | undefined, location)).toEqual(expected);
    });
});

describe("defaultFileLocation", () => {
    it("reads the location of a File default", () => {
        expect(defaultFileLocation({ input: { default: { class: "File", location: OLD } } })).toBe(OLD);
        expect(defaultFileLocation({ input: { default: 5 } })).toBe("");
        expect(defaultFileLocation(undefined)).toBe("");
    });
});
