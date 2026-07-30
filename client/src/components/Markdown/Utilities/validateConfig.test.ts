import { describe, expect, it } from "vitest";

import { validateConfig } from "./validateConfig";

// A schema shaped like the server export: settings is a closed object, tracks is a
// list of open objects, the top level allows binding/meta keys, and a conditional
// is an optional discriminated union.
const SCHEMA = {
    type: "object",
    additionalProperties: true,
    properties: {
        settings: {
            anyOf: [
                {
                    type: "object",
                    additionalProperties: false,
                    properties: {
                        locus: { anyOf: [{ type: "string" }, { type: "null" }], default: null },
                        source: {
                            anyOf: [
                                {
                                    oneOf: [
                                        {
                                            type: "object",
                                            properties: { origin: { const: "remote" }, url: { type: "string" } },
                                            required: ["origin"],
                                        },
                                        {
                                            type: "object",
                                            properties: { origin: { const: "history" }, dataset: { type: "string" } },
                                            required: ["origin"],
                                        },
                                    ],
                                },
                                { type: "null" },
                            ],
                            default: null,
                        },
                    },
                },
                { type: "null" },
            ],
            default: null,
        },
        tracks: {
            type: "array",
            items: {
                type: "object",
                additionalProperties: true,
                properties: {
                    type: {
                        anyOf: [{ enum: ["auto", "annotation", "snp"], type: "string" }, { type: "null" }],
                        default: "auto",
                    },
                },
            },
            default: [],
        },
    },
};

describe("validateConfig", () => {
    it("returns no warnings for a valid config", () => {
        expect(validateConfig(SCHEMA, { settings: { locus: "chr1" }, tracks: [{ type: "snp" }] })).toEqual([]);
    });

    it("allows an empty config and binding/meta keys", () => {
        expect(validateConfig(SCHEMA, {})).toEqual([]);
        expect(validateConfig(SCHEMA, { visualization_name: "igv", dataset_id: "x", height: 400 })).toEqual([]);
    });

    it("flags an unknown settings key", () => {
        expect(validateConfig(SCHEMA, { settings: { bogus: 1 } })).toEqual(['settings: unexpected property "bogus"']);
    });

    it("flags a bad select choice with the allowed values", () => {
        expect(validateConfig(SCHEMA, { tracks: [{ type: "nope" }] })).toEqual([
            "tracks.0.type: must be one of: auto, annotation, snp",
        ]);
    });

    it("flags a wrong type", () => {
        expect(validateConfig(SCHEMA, { settings: { locus: 123 } })).toEqual(["settings.locus: must be string"]);
    });

    it("collapses a conditional's per-branch failures into one choice list", () => {
        expect(validateConfig(SCHEMA, { settings: { source: { origin: "nope" } } })).toEqual([
            "settings.source.origin: must be one of: remote, history",
        ]);
    });

    it("never throws on an uncompilable schema", () => {
        expect(validateConfig({ type: "not-a-real-type" }, { anything: true })).toEqual([]);
    });
});
