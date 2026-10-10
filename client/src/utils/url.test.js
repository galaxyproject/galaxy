import { describe, expect, it } from "vitest";

import { addSearchParams, isUrl, isValidNetworkUrl, isValidUrl } from "./url";

describe("addSearchParams", () => {
    it("preserves the URL when no parameters are supplied", () => {
        expect(addSearchParams("/test?name=value")).toBe("/test?name=value");
    });

    it("starts a query string when the URL has none", () => {
        expect(addSearchParams("/test", { name: "value", and: "this" })).toBe("/test?name=value&and=this");
    });

    it("appends parameters to an existing query string", () => {
        expect(addSearchParams("/test?exists=value", { name: "value" })).toBe("/test?exists=value&name=value");
    });
});

describe("isUrl", () => {
    it("rejects an unknown scheme", () => {
        expect(isUrl("xyz://")).toBeFalsy();
    });

    it.each(["ftp://", "http://"])("recognizes the supported prefix %j without a hostname", (url) => {
        expect(isUrl(url)).toBeTruthy();
    });
});

describe("isValidNetworkUrl", () => {
    it.each(["https://example.com/x", "http://sub.example.org/path?q=1", "ftp://ftp.example.org/a"])(
        "accepts the well-formed network URL %j",
        (url) => {
            expect(isValidNetworkUrl(url)).toBe(true);
        },
    );

    it.each(["https://.../foo", "https://./foo", "https://..example.com/x", "https:///foo"])(
        "rejects the missing hostname or empty DNS labels in %j",
        (url) => {
            expect(isValidNetworkUrl(url)).toBe(false);
        },
    );

    it.each(["gxfiles://foo", "drs://example.org/123", "not-a-url"])("rejects the non-network input %j", (url) => {
        expect(isValidNetworkUrl(url)).toBe(false);
    });
});

describe("isValidUrl", () => {
    it.each([
        "gxfiles://myftp/file.txt",
        "gxuserfiles://mysource/x",
        "drs://example.org/abc",
        "zenodo://record/123",
        "invenio://record/123",
        "dataverse://doi/x",
        "base64://aGVsbG8=",
    ])("accepts the custom file-source URL %j", (url) => {
        expect(isValidUrl(url)).toBe(true);
    });

    it.each(["https://example.com/", "https://example.com/file.txt", "ftp://ftp.example.org/a"])(
        "accepts the well-formed network URL %j",
        (url) => {
            expect(isValidUrl(url)).toBe(true);
        },
    );

    it.each(["https://.../foo", "https://./foo", "https:///foo"])(
        "rejects the missing hostname or empty DNS labels in %j",
        (url) => {
            expect(isValidUrl(url)).toBe(false);
        },
    );

    it.each(["", "not-a-url", "xyz://foo"])("rejects the empty, non-URL, or unknown-scheme input %j", (url) => {
        expect(isValidUrl(url)).toBe(false);
    });

    it.each(["  https://example.com/x  ", "\thttps://example.com/x\n", "   gxfiles://myftp/file.txt   "])(
        "accepts the valid URL with surrounding whitespace %j",
        (url) => {
            expect(isValidUrl(url)).toBe(true);
        },
    );

    it.each(["   ", "  https://.../x  "])("rejects the invalid URL after trimming whitespace in %j", (url) => {
        expect(isValidUrl(url)).toBe(false);
    });
});
