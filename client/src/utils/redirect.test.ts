import { describe, expect, it, test, vi } from "vitest";

import { getAppRoot } from "@/onload/loadConfig";

import { safeRedirectPath, withPrefix } from "./redirect";

vi.mock("@/onload/loadConfig");

test("route prefix changes", async () => {
    vi.mocked(getAppRoot).mockReturnValue("/prefix");
    // test routes
    expect(withPrefix("http://")).toEqual("http://");
    expect(withPrefix("/")).toEqual("/prefix/");
    expect(withPrefix("/home")).toEqual("/prefix/home");
    // keep protocols in query parameters intact
    expect(withPrefix("/authz/cilogon/login?idphint=https://test.com")).toEqual(
        "/prefix/authz/cilogon/login?idphint=https://test.com",
    );
    // ensure that it can only be called once
    expect(withPrefix(withPrefix("/home"))).toEqual("/prefix/prefix/home");
    // This doesn't do what it looks like it should do?
});

describe("safeRedirectPath", () => {
    it("accepts relative paths, query string and all", () => {
        expect(safeRedirectPath("/")).toEqual("/");
        expect(safeRedirectPath("/tool_landings/1234-5678?public=true")).toEqual(
            "/tool_landings/1234-5678?public=true",
        );
        expect(safeRedirectPath("/histories/list#anchor")).toEqual("/histories/list#anchor");
    });

    it("rejects anything pointing off this Galaxy", () => {
        expect(safeRedirectPath("https://evil.example.com/")).toBeUndefined();
        expect(safeRedirectPath("http://evil.example.com/")).toBeUndefined();
        // protocol-relative -- the browser reads these as another origin
        expect(safeRedirectPath("//evil.example.com/")).toBeUndefined();
        expect(safeRedirectPath("/\\evil.example.com/")).toBeUndefined();
        // browsers strip tabs and newlines, so this reaches the network as "//evil.example.com"
        expect(safeRedirectPath("/\t/evil.example.com")).toBeUndefined();
        expect(safeRedirectPath("/\n/evil.example.com")).toBeUndefined();
        expect(safeRedirectPath(" //evil.example.com")).toBeUndefined();
    });

    it("refuses control characters outright", () => {
        // Accepting these would hand on a value whose meaning changes when it is resolved.
        expect(safeRedirectPath("/foo\tbar")).toBeUndefined();
        expect(safeRedirectPath("/foo\nbar")).toBeUndefined();
        expect(safeRedirectPath("/foo\u0000bar")).toBeUndefined();
        expect(safeRedirectPath("/foo\u007fbar")).toBeUndefined();
        expect(safeRedirectPath(" /histories/list")).toBeUndefined();
        expect(safeRedirectPath("/histories/list ")).toBeUndefined();
    });

    it("rejects non-paths and empty values", () => {
        expect(safeRedirectPath(undefined)).toBeUndefined();
        expect(safeRedirectPath(null)).toBeUndefined();
        expect(safeRedirectPath("")).toBeUndefined();
        expect(safeRedirectPath("histories/list")).toBeUndefined();
        // vue-router hands back an array when a param is repeated
        expect(safeRedirectPath(["/histories/list"])).toBeUndefined();
    });
});
