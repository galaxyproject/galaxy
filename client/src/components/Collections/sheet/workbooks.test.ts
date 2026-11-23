import { describe, expect, test } from "vitest";

import { guessUriFilename, withAutoListIdentifiers } from "./workbooks";

describe("guessUriFilename", () => {
    test("uses the last path segment without its query", () => {
        expect(guessUriFilename("https://example.org/data/a.bed?download=1")).toBe("a.bed");
    });

    test("leaves out the userinfo of a pathless URL", () => {
        expect(guessUriFilename("https://user:secret@example.org")).toBe("example.org");
    });

    test("leaves out the userinfo of a nested URL", () => {
        expect(guessUriFilename("https://example.org/a?next=ftp://user:secret@inner")).toBe("inner");
        expect(guessUriFilename("https://example.org/ftp://user:secret@inner.bed")).toBe("inner.bed");
    });
});

describe("withAutoListIdentifiers", () => {
    test("uses the last path segment without its extension and keeps the URI", () => {
        const uri = "https://example.org/data/a.bed";
        expect(withAutoListIdentifiers([[uri]])).toEqual([[uri, "a"]]);
    });

    test("leaves out the userinfo of a pathless URL", () => {
        const uri = "https://user:secret@example.org";
        expect(withAutoListIdentifiers([[uri]])).toEqual([[uri, "example"]]);
    });

    test("leaves out the userinfo of a nested URL", () => {
        const uri = "https://example.org/a?next=ftp://user:secret@inner.bed";
        expect(withAutoListIdentifiers([[uri]])).toEqual([[uri, "inner"]]);
    });
});
