import { beforeEach, describe, expect, it, vi } from "vitest";

import { getAppRoot } from "@/onload/loadConfig";

import { safeRedirectPath, withPrefix } from "./redirect";

vi.mock("@/onload/loadConfig");

describe("withPrefix", () => {
    beforeEach(() => {
        vi.mocked(getAppRoot).mockReturnValue("/prefix");
    });

    it.each([
        { name: "leaves a protocol unchanged", input: "http://", expected: "http://" },
        { name: "prefixes the root path", input: "/", expected: "/prefix/" },
        { name: "prefixes a route", input: "/home", expected: "/prefix/home" },
        {
            name: "preserves a protocol inside query parameters",
            input: "/authz/cilogon/login?idphint=https://test.com",
            expected: "/prefix/authz/cilogon/login?idphint=https://test.com",
        },
    ])("$name", ({ input, expected }) => {
        expect(withPrefix(input)).toEqual(expected);
    });

    it("adds the prefix again when called twice", () => {
        expect(withPrefix(withPrefix("/home"))).toEqual("/prefix/prefix/home");
    });
});

describe("safeRedirectPath", () => {
    it.each([
        { name: "the root path", path: "/" },
        { name: "a path with a query string", path: "/tool_landings/1234-5678?public=true" },
        { name: "a path with an anchor", path: "/histories/list#anchor" },
    ])("accepts $name", ({ path }) => {
        expect(safeRedirectPath(path)).toEqual(path);
    });

    it.each([
        { name: "an HTTPS URL", path: "https://evil.example.com/" },
        { name: "an HTTP URL", path: "http://evil.example.com/" },
        { name: "a protocol-relative URL", path: "//evil.example.com/" },
        { name: "a backslash normalized to a second slash", path: "/\\evil.example.com/" },
        { name: "a tab between slashes", path: "/\t/evil.example.com" },
        { name: "a newline between slashes", path: "/\n/evil.example.com" },
        { name: "a space before a protocol-relative URL", path: " //evil.example.com" },
    ])("rejects $name pointing outside this Galaxy", ({ path }) => {
        expect(safeRedirectPath(path)).toBeUndefined();
    });

    // Browsers discard these characters when resolving URLs, changing the target.
    it.each([
        { name: "a tab", path: "/foo\tbar" },
        { name: "a newline", path: "/foo\nbar" },
        { name: "a null character", path: "/foo\u0000bar" },
        { name: "a DEL character", path: "/foo\u007fbar" },
        { name: "leading whitespace", path: " /histories/list" },
        { name: "trailing whitespace", path: "/histories/list " },
    ])("rejects a path containing $name", ({ path }) => {
        expect(safeRedirectPath(path)).toBeUndefined();
    });

    it.each([
        { name: "undefined", path: undefined },
        { name: "null", path: null },
        { name: "an empty string", path: "" },
        { name: "a path without a leading slash", path: "histories/list" },
        { name: "an array from a repeated vue-router parameter", path: ["/histories/list"] },
    ])("rejects $name", ({ path }) => {
        expect(safeRedirectPath(path)).toBeUndefined();
    });
});
