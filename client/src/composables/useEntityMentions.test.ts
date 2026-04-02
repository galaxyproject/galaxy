import { describe, expect, it } from "vitest";

import { buildEntityContext, detectMentionTrigger, parseMentions, type ResolvedEntity } from "./useEntityMentions";

describe("detectMentionTrigger", () => {
    it("returns null when no @ is present", () => {
        expect(detectMentionTrigger("hello world", 5)).toBeNull();
    });

    it("detects bare @ at start of input", () => {
        const result = detectMentionTrigger("@", 1);
        expect(result).toEqual({
            entityType: null,
            searchText: "",
            startIndex: 0,
            endIndex: 1,
        });
    });

    it("detects partial entity type", () => {
        const result = detectMentionTrigger("@dat", 4);
        expect(result).toEqual({
            entityType: null,
            searchText: "dat",
            startIndex: 0,
            endIndex: 4,
        });
    });

    it("detects entity type with colon", () => {
        const result = detectMentionTrigger("@dataset:", 9);
        expect(result).toEqual({
            entityType: "dataset",
            searchText: "",
            startIndex: 0,
            endIndex: 9,
        });
    });

    it("detects entity type with search text", () => {
        const result = detectMentionTrigger("@dataset:42", 11);
        expect(result).toEqual({
            entityType: "dataset",
            searchText: "42",
            startIndex: 0,
            endIndex: 11,
        });
    });

    it("detects history type", () => {
        const result = detectMentionTrigger("@history:current", 16);
        expect(result).toEqual({
            entityType: "history",
            searchText: "current",
            startIndex: 0,
            endIndex: 16,
        });
    });

    it("detects mention after whitespace", () => {
        const result = detectMentionTrigger("hello @dat", 10);
        expect(result).toEqual({
            entityType: null,
            searchText: "dat",
            startIndex: 6,
            endIndex: 10,
        });
    });

    it("returns null when @ is mid-word", () => {
        expect(detectMentionTrigger("foo@bar", 7)).toBeNull();
    });

    it("returns null when cursor is past the mention (space after)", () => {
        expect(detectMentionTrigger("@dataset:42 more text", 15)).toBeNull();
    });

    it("handles multiple @ signs and picks the last one", () => {
        const result = detectMentionTrigger("@dataset:42 @hist", 17);
        expect(result).toEqual({
            entityType: null,
            searchText: "hist",
            startIndex: 12,
            endIndex: 17,
        });
    });

    it("is case-insensitive for entity type", () => {
        const result = detectMentionTrigger("@Dataset:", 9);
        expect(result).toEqual({
            entityType: "dataset",
            searchText: "",
            startIndex: 0,
            endIndex: 9,
        });
    });
});

describe("parseMentions", () => {
    it("returns empty array for text with no mentions", () => {
        expect(parseMentions("just some text")).toEqual([]);
    });

    it("parses a single dataset mention", () => {
        expect(parseMentions("look at @dataset:42 please")).toEqual([
            { type: "dataset", identifier: "42", startIndex: 8, endIndex: 19 },
        ]);
    });

    it("parses a history mention", () => {
        expect(parseMentions("in @history:current")).toEqual([
            { type: "history", identifier: "current", startIndex: 3, endIndex: 19 },
        ]);
    });

    it("parses multiple mentions", () => {
        const result = parseMentions("compare @dataset:1 with @dataset:2");
        expect(result).toHaveLength(2);
        expect(result[0]!.identifier).toBe("1");
        expect(result[1]!.identifier).toBe("2");
    });

    it("parses mixed entity types", () => {
        const result = parseMentions("@dataset:10 in @history:current");
        expect(result).toHaveLength(2);
        expect(result[0]!.type).toBe("dataset");
        expect(result[1]!.type).toBe("history");
    });
});

describe("buildEntityContext", () => {
    const dataset: ResolvedEntity = {
        type: "dataset",
        identifier: "42",
        id: "abc123",
        name: "Mapped reads",
        extension: "bam",
        state: "ok",
        hid: 42,
    };

    const history: ResolvedEntity = {
        type: "history",
        identifier: "current",
        id: "def456",
        name: "RNA-seq analysis",
    };

    it("returns null for empty entity list", () => {
        expect(buildEntityContext([])).toBeNull();
    });

    it("groups datasets and histories", () => {
        const result = buildEntityContext([dataset, history]);
        expect(result).toEqual({
            datasets: [dataset],
            histories: [history],
        });
    });

    it("returns null when no entities resolve", () => {
        expect(buildEntityContext([])).toBeNull();
    });

    it("handles datasets only", () => {
        const result = buildEntityContext([dataset]);
        expect(result).toEqual({
            datasets: [dataset],
            histories: [],
        });
    });

    it("handles histories only", () => {
        const result = buildEntityContext([history]);
        expect(result).toEqual({
            datasets: [],
            histories: [history],
        });
    });
});
