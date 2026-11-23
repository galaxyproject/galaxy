import { describe, expect, it } from "vitest";

import {
    isLinkFromSource,
    isPickerCancel,
    isPickerHello,
    isPickerNonce,
    isPickerResult,
    makeNonce,
    parseReturnOrigin,
    parseSourceUrl,
} from "./pickerProtocol";

const UUID = "0f8fad5b-d9cb-469f-a165-70867728950e";
const ITEM = { type: "dataset", name: "reads.bed", link: `https://usegalaxy.eu/api/short_term_storage/${UUID}` };
const HELLO = { type: "galaxy-picker/hello", protocol: 1, version: "27.0", root: "https://usegalaxy.eu/", nonce: "n1" };

describe("isPickerHello", () => {
    it.each([[HELLO], [{ ...HELLO, version: "" }], [{ ...HELLO, root: "https://example.org/galaxy/" }]])(
        "accepts %j",
        (message) => {
            expect(isPickerHello(message)).toBe(true);
        },
    );

    it.each([
        [null],
        [undefined],
        ["galaxy-picker/hello"],
        [[HELLO]],
        [{ ...HELLO, type: "galaxy-picker/result" }],
        [{ ...HELLO, protocol: 2 }],
        [{ ...HELLO, protocol: "1" }],
        [{ ...HELLO, protocol: undefined }],
        [{ ...HELLO, version: undefined }],
        [{ ...HELLO, version: 27 }],
        [{ ...HELLO, root: undefined }],
        [{ ...HELLO, root: "" }],
        [{ ...HELLO, root: ["https://usegalaxy.eu/"] }],
        [{ ...HELLO, nonce: undefined }],
        [{ ...HELLO, nonce: "" }],
        [{ ...HELLO, nonce: 1 }],
    ])("rejects %j", (message) => {
        expect(isPickerHello(message)).toBe(false);
    });
});

describe("isPickerResult", () => {
    it.each([
        [{ type: "galaxy-picker/result", protocol: 1, nonce: "n1", items: [], failed: 0 }],
        [{ type: "galaxy-picker/result", protocol: 1, nonce: "n1", items: [ITEM], failed: 2 }],
        [
            {
                type: "galaxy-picker/result",
                protocol: 1,
                nonce: "n1",
                items: [ITEM, { ...ITEM, type: "dataset_collection", name: "" }],
                failed: 0,
            },
        ],
    ])("accepts %j", (message) => {
        expect(isPickerResult(message)).toBe(true);
    });

    it.each([
        [null],
        ["galaxy-picker/result"],
        [{ type: "galaxy-picker/hello", protocol: 1, nonce: "n1", items: [] }],
        [{ type: "galaxy-picker/result", protocol: 2, nonce: "n1", items: [], failed: 0 }],
        [{ type: "galaxy-picker/result", nonce: "n1", items: [], failed: 0 }],
        [{ type: "galaxy-picker/result", protocol: 1, items: [], failed: 0 }],
        [{ type: "galaxy-picker/result", protocol: 1, nonce: "", items: [], failed: 0 }],
        [{ type: "galaxy-picker/result", protocol: 1, nonce: 1, items: [], failed: 0 }],
        [{ type: "galaxy-picker/result", protocol: 1, nonce: "n1" }],
        [{ type: "galaxy-picker/result", protocol: 1, nonce: "n1", items: ITEM, failed: 0 }],
        [{ type: "galaxy-picker/result", protocol: 1, nonce: "n1", items: [null], failed: 0 }],
        [{ type: "galaxy-picker/result", protocol: 1, nonce: "n1", items: ["link"], failed: 0 }],
        [{ type: "galaxy-picker/result", protocol: 1, nonce: "n1", items: [{ ...ITEM, type: "history" }], failed: 0 }],
        [{ type: "galaxy-picker/result", protocol: 1, nonce: "n1", items: [{ ...ITEM, type: undefined }], failed: 0 }],
        [{ type: "galaxy-picker/result", protocol: 1, nonce: "n1", items: [{ ...ITEM, name: 1 }], failed: 0 }],
        [{ type: "galaxy-picker/result", protocol: 1, nonce: "n1", items: [{ ...ITEM, link: "" }], failed: 0 }],
        [{ type: "galaxy-picker/result", protocol: 1, nonce: "n1", items: [{ ...ITEM, link: ["x"] }], failed: 0 }],
        [
            {
                type: "galaxy-picker/result",
                protocol: 1,
                nonce: "n1",
                items: [ITEM, { ...ITEM, link: undefined }],
                failed: 0,
            },
        ],
        [{ type: "galaxy-picker/result", protocol: 1, nonce: "n1", items: [ITEM] }],
        [{ type: "galaxy-picker/result", protocol: 1, nonce: "n1", items: [ITEM], failed: -1 }],
        [{ type: "galaxy-picker/result", protocol: 1, nonce: "n1", items: [ITEM], failed: 1.5 }],
        [{ type: "galaxy-picker/result", protocol: 1, nonce: "n1", items: [ITEM], failed: "1" }],
    ])("rejects %j", (message) => {
        expect(isPickerResult(message)).toBe(false);
    });
});

describe("isPickerNonce", () => {
    it.each([["0123456789abcdef0123456789abcdef"], ["A".repeat(16)], ["a_b-c".repeat(25)]])("accepts %s", (nonce) => {
        expect(isPickerNonce(nonce)).toBe(true);
    });

    it.each([
        [undefined],
        [null],
        [1234],
        [""],
        ["a".repeat(15)],
        ["a".repeat(129)],
        ["<script>alert(1)"],
        ["0123456789abcdef 0123456789abcdef"],
        [["0123456789abcdef"]],
    ])("rejects %j", (nonce) => {
        expect(isPickerNonce(nonce)).toBe(false);
    });

    it("accepts what makeNonce makes", () => {
        expect(isPickerNonce(makeNonce())).toBe(true);
    });
});

describe("isPickerCancel", () => {
    it("accepts a cancel with its nonce", () => {
        expect(isPickerCancel({ type: "galaxy-picker/cancel", nonce: "n1" })).toBe(true);
    });

    it.each([
        [null],
        ["galaxy-picker/cancel"],
        [{ type: "galaxy-picker/cancel" }],
        [{ type: "galaxy-picker/cancel", nonce: "" }],
        [{ type: "galaxy-picker/cancel", nonce: 1 }],
        [{ type: "galaxy-picker/result", nonce: "n1" }],
    ])("rejects %j", (message) => {
        expect(isPickerCancel(message)).toBe(false);
    });
});

describe("parseReturnOrigin", () => {
    it.each([
        ["https://usegalaxy.org", "https://usegalaxy.org"],
        ["https://usegalaxy.org/", "https://usegalaxy.org"],
        ["https://usegalaxy.org:8443", "https://usegalaxy.org:8443"],
        ["https://usegalaxy.org:443/", "https://usegalaxy.org"],
        ["HTTPS://UseGalaxy.ORG", "https://usegalaxy.org"],
        ["https://xn--bcher-kva.example", "https://xn--bcher-kva.example"],
        ["https://192.0.2.1", "https://192.0.2.1"],
        ["http://localhost:8080", "http://localhost:8080"],
        ["http://localhost", "http://localhost"],
        ["http://localhost:80/", "http://localhost"],
        ["http://127.0.0.1:8081/", "http://127.0.0.1:8081"],
        ["http://[::1]:8080", "http://[::1]:8080"],
        ["https://[::1]", "https://[::1]"],
    ])("accepts %s as %s", (raw, origin) => {
        expect(parseReturnOrigin(raw)).toBe(origin);
    });

    it.each([
        [undefined],
        [null],
        [42],
        [["https://usegalaxy.org"]],
        [""],
        ["usegalaxy.org"],
        ["//usegalaxy.org"],
        ["https:usegalaxy.org"],
        ["https:/usegalaxy.org"],
        ["https:///usegalaxy.org"],
        ["http://usegalaxy.org"],
        ["http://localhost.example.org"],
        ["http://127.0.0.2"],
        ["ftp://usegalaxy.org"],
        ["javascript:alert(1)"],
        ["data:text/html,hi"],
        ["https://usegalaxy.org/galaxy"],
        ["https://usegalaxy.org/galaxy/"],
        ["https://usegalaxy.org//"],
        ["https://usegalaxy.org/?"],
        ["https://usegalaxy.org?x=1"],
        ["https://usegalaxy.org/#"],
        ["https://usegalaxy.org#top"],
        ["https://user@usegalaxy.org"],
        ["https://user:pass@usegalaxy.org/"],
        ["https://usegalaxy.org@evil.example"],
        ["https://evil.example\\@usegalaxy.org"],
        ["https://evil.example\\usegalaxy.org"],
        ["https://evil.example#@usegalaxy.org"],
        [" https://usegalaxy.org"],
        ["https://usegalaxy.org "],
        ["https://usegalaxy.org\n"],
        ["https://usegalaxy\t.org"],
        ["https://usegalaxy.org\u0000"],
        ["https://usegalaxy%2eorg"],
        ["https://usegalaxy．org"],
        ["https://bücher.example"],
        ["https://0x7f.1"],
        ["https://usegalaxy.org:"],
        ["https://usegalaxy.org:0443"],
        ["https://usegalaxy.org:99999"],
        ["https://"],
    ])("rejects %j", (raw) => {
        expect(parseReturnOrigin(raw)).toBeNull();
    });
});

describe("parseSourceUrl", () => {
    it.each([
        ["https://usegalaxy.eu", "https://usegalaxy.eu", "https://usegalaxy.eu/"],
        ["https://usegalaxy.eu/", "https://usegalaxy.eu", "https://usegalaxy.eu/"],
        ["usegalaxy.eu", "https://usegalaxy.eu", "https://usegalaxy.eu/"],
        ["  https://usegalaxy.eu/  ", "https://usegalaxy.eu", "https://usegalaxy.eu/"],
        ["HTTPS://UseGalaxy.EU:443", "https://usegalaxy.eu", "https://usegalaxy.eu/"],
        ["https://example.org/galaxy", "https://example.org", "https://example.org/galaxy/"],
        ["https://example.org/galaxy/", "https://example.org", "https://example.org/galaxy/"],
        ["example.org:8443/galaxy/", "https://example.org:8443", "https://example.org:8443/galaxy/"],
        ["localhost:8080", "https://localhost:8080", "https://localhost:8080/"],
        ["http://localhost:8080", "http://localhost:8080", "http://localhost:8080/"],
        ["http://127.0.0.1:8080/galaxy", "http://127.0.0.1:8080", "http://127.0.0.1:8080/galaxy/"],
        ["http://[::1]:8080/", "http://[::1]:8080", "http://[::1]:8080/"],
    ])("reads %s as %s with root %s", (raw, origin, root) => {
        expect(parseSourceUrl(raw)).toEqual({ origin, root });
    });

    it.each([
        [undefined],
        [null],
        [{}],
        [""],
        ["   "],
        ["http://usegalaxy.eu"],
        ["http://example.org:8080/galaxy"],
        ["ftp://usegalaxy.eu"],
        ["javascript:alert(1)"],
        ["//usegalaxy.eu"],
        ["https:usegalaxy.eu"],
        ["https:///usegalaxy.eu"],
        ["https://usegalaxy.eu/?"],
        ["https://usegalaxy.eu/?x=1"],
        ["https://usegalaxy.eu/#"],
        ["https://usegalaxy.eu/galaxy#top"],
        ["https://user@usegalaxy.eu"],
        ["https://user:pass@usegalaxy.eu/galaxy/"],
        ["https://evil.example\\@usegalaxy.eu"],
        ["https://usegalaxy.eu\\galaxy"],
        ["https://usegalaxy.eu/gal axy"],
        ["https://usegalaxy.eu/gal\taxy"],
        ["https://usegalaxy%2eeu"],
        ["https://usegalaxy．eu"],
        ["https://0x7f.1"],
        ["https://usegalaxy.eu/galaxy/../admin"],
        ["https://usegalaxy.eu/./galaxy"],
        ["https://usegalaxy.eu/galáxy"],
    ])("rejects %j", (raw) => {
        expect(parseSourceUrl(raw)).toBeNull();
    });
});

describe("isLinkFromSource", () => {
    it.each([
        [`https://usegalaxy.eu/api/short_term_storage/${UUID}`, "https://usegalaxy.eu/"],
        [`https://usegalaxy.eu/api/short_term_storage/${UUID.toUpperCase()}`, "https://usegalaxy.eu/"],
        [`https://example.org/galaxy/api/short_term_storage/${UUID}`, "https://example.org/galaxy/"],
        [`http://localhost:8080/api/short_term_storage/${UUID}`, "http://localhost:8080/"],
    ])("accepts %s from %s", (link, root) => {
        expect(isLinkFromSource(link, root)).toBe(true);
    });

    it.each([
        [undefined, "https://usegalaxy.eu/"],
        [null, "https://usegalaxy.eu/"],
        [42, "https://usegalaxy.eu/"],
        ["", "https://usegalaxy.eu/"],
        [`https://usegalaxy.org/api/short_term_storage/${UUID}`, "https://usegalaxy.eu/"],
        [`https://usegalaxy.eu.evil.example/api/short_term_storage/${UUID}`, "https://usegalaxy.eu/"],
        [`https://usegalaxy.eu/api/short_term_storage/${UUID}`, "https://usegalaxy.eu/galaxy/"],
        [`https://usegalaxy.eu/galaxy/api/short_term_storage/${UUID}`, "https://usegalaxy.eu/"],
        [`http://usegalaxy.eu/api/short_term_storage/${UUID}`, "https://usegalaxy.eu/"],
        [`https://usegalaxy.eu/api/short_term_storage/`, "https://usegalaxy.eu/"],
        [`https://usegalaxy.eu/api/short_term_storage/req1`, "https://usegalaxy.eu/"],
        [`https://usegalaxy.eu/api/short_term_storage/${UUID}/`, "https://usegalaxy.eu/"],
        [`https://usegalaxy.eu/api/short_term_storage/${UUID}/ready`, "https://usegalaxy.eu/"],
        [`https://usegalaxy.eu/api/short_term_storage/${UUID}?x=1`, "https://usegalaxy.eu/"],
        [`https://usegalaxy.eu/api/short_term_storage/${UUID}#x`, "https://usegalaxy.eu/"],
        [`https://usegalaxy.eu/api/short_term_storage/${UUID.replaceAll("-", "")}`, "https://usegalaxy.eu/"],
        [`https://usegalaxy.eu/api/short_term_storage/../datasets/${UUID}`, "https://usegalaxy.eu/"],
        [`https://usegalaxy.eu/api/datasets/${UUID}`, "https://usegalaxy.eu/"],
        [` https://usegalaxy.eu/api/short_term_storage/${UUID}`, "https://usegalaxy.eu/"],
    ])("rejects %j from %s", (link, root) => {
        expect(isLinkFromSource(link, root)).toBe(false);
    });
});

describe("makeNonce", () => {
    it("makes 128 random bits as hex", () => {
        const nonces = new Set(Array.from({ length: 20 }, () => makeNonce()));
        expect(nonces.size).toBe(20);
        nonces.forEach((nonce) => expect(nonce).toMatch(/^[0-9a-f]{32}$/));
    });
});
