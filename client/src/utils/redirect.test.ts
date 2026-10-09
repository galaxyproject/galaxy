import { beforeEach, describe, expect, it, vi } from "vitest";

import { getAppRoot } from "@/onload/loadConfig";

import { safeLoginRedirect, safeRedirectPath, withPrefix } from "./redirect";

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

describe("safeLoginRedirect", () => {
    // Keep in step with test/unit/util/test_safe_local_redirect.py, which checks the server side.
    const allowedHosts = ["tools.example.org", "data.example.org:8443", "[2001:db8::1]"];

    it.each([
        "https://tools.example.org/landing",
        "https://TOOLS.example.org/landing",
        "https://tools.example.org:443/landing",
        "https://data.example.org:8443/back",
        "https://[2001:db8::1]/back",
    ])("accepts %s", (target) => {
        expect(safeLoginRedirect(target, allowedHosts)).toEqual(target);
    });

    it.each([
        "https://evil.example.com/",
        "https://tools.example.org.evil.com/",
        "https://eviltools.example.org/",
        "https://tools\uFF0Eexample\uFF0Eorg/",
        "https://tools%2eexample.org/",
        "https://tools.example.org:8443/",
        "https://data.example.org/",
        "http://tools.example.org/",
        "https:tools.example.org",
        "https:///tools.example.org",
        "https://tools.example.org@evil.com/",
        "https://user:pass@tools.example.org/",
        "https://evil.com\\@tools.example.org/",
        "https://tools.example.org\\.evil.com/",
        "https://evil.com#@tools.example.org",
        "https://tools.example.org:notaport/",
        "https://tools.example.org/\tpath",
        " https://tools.example.org/",
    ])("refuses %j", (target) => {
        expect(safeLoginRedirect(target, allowedHosts)).toBeUndefined();
    });

    it("refuses external URLs without allowed hosts", () => {
        expect(safeLoginRedirect("https://tools.example.org/", [])).toBeUndefined();
    });
});
