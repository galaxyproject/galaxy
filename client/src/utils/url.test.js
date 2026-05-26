import { describe, expect, it, test } from "vitest";

import { addSearchParams, isUrl, isValidNetworkUrl, isValidUrl } from "./url";

describe("test url utilities", () => {
    it("adding parameters to url", async () => {
        expect(addSearchParams("/test?name=value")).toBe("/test?name=value");
        expect(addSearchParams("/test", { name: "value", and: "this" })).toBe("/test?name=value&and=this");
        expect(addSearchParams("/test?exists=value", { name: "value" })).toBe("/test?exists=value&name=value");
    });

    test("url detection", () => {
        expect(isUrl("xyz://")).toBeFalsy();
        expect(isUrl("ftp://")).toBeTruthy();
        expect(isUrl("http://")).toBeTruthy();
    });

    test("network url validation accepts well-formed hosts", () => {
        expect(isValidNetworkUrl("https://example.com/x")).toBe(true);
        expect(isValidNetworkUrl("http://sub.example.org/path?q=1")).toBe(true);
        expect(isValidNetworkUrl("ftp://ftp.example.org/a")).toBe(true);
    });

    test("network url validation rejects empty DNS labels", () => {
        expect(isValidNetworkUrl("https://.../foo")).toBe(false);
        expect(isValidNetworkUrl("https://./foo")).toBe(false);
        expect(isValidNetworkUrl("https://..example.com/x")).toBe(false);
        expect(isValidNetworkUrl("https:///foo")).toBe(false);
    });

    test("network url validation rejects non-network schemes", () => {
        expect(isValidNetworkUrl("gxfiles://foo")).toBe(false);
        expect(isValidNetworkUrl("drs://example.org/123")).toBe(false);
        expect(isValidNetworkUrl("not-a-url")).toBe(false);
    });

    test("isValidUrl accepts custom Galaxy file-source schemes", () => {
        expect(isValidUrl("gxfiles://myftp/file.txt")).toBe(true);
        expect(isValidUrl("gxuserfiles://mysource/x")).toBe(true);
        expect(isValidUrl("drs://example.org/abc")).toBe(true);
        expect(isValidUrl("zenodo://record/123")).toBe(true);
        expect(isValidUrl("invenio://record/123")).toBe(true);
        expect(isValidUrl("dataverse://doi/x")).toBe(true);
        expect(isValidUrl("base64://aGVsbG8=")).toBe(true);
    });

    test("isValidUrl accepts well-formed network urls", () => {
        expect(isValidUrl("https://example.com/")).toBe(true);
        expect(isValidUrl("https://example.com/file.txt")).toBe(true);
        expect(isValidUrl("ftp://ftp.example.org/a")).toBe(true);
    });

    test("isValidUrl rejects network urls with empty DNS labels", () => {
        expect(isValidUrl("https://.../foo")).toBe(false);
        expect(isValidUrl("https://./foo")).toBe(false);
        expect(isValidUrl("https:///foo")).toBe(false);
    });

    test("isValidUrl rejects unknown schemes and non-urls", () => {
        expect(isValidUrl("")).toBe(false);
        expect(isValidUrl("not-a-url")).toBe(false);
        expect(isValidUrl("xyz://foo")).toBe(false);
    });

    test("isValidUrl tolerates surrounding whitespace", () => {
        expect(isValidUrl("  https://example.com/x  ")).toBe(true);
        expect(isValidUrl("\thttps://example.com/x\n")).toBe(true);
        expect(isValidUrl("   gxfiles://myftp/file.txt   ")).toBe(true);
        expect(isValidUrl("   ")).toBe(false);
        expect(isValidUrl("  https://.../x  ")).toBe(false);
    });
});
