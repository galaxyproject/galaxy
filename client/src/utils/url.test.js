import { describe, expect, it, test } from "vitest";

import { addSearchParams, extractNameFromUrl, isUrl, isValidNetworkUrl, isValidUrl, urlWithoutUserinfo } from "./url";

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

    test("urlWithoutUserinfo removes the userinfo of a url", () => {
        expect(urlWithoutUserinfo("https://user:secret@example.org/a.bed")).toBe("https://example.org/a.bed");
        expect(urlWithoutUserinfo("https://user:secret@example.org")).toBe("https://example.org");
        expect(urlWithoutUserinfo("ftp://user:p@ss@example.org/a")).toBe("ftp://example.org/a");
        expect(urlWithoutUserinfo("https://user:se?cret@example.org/a")).toBe("https://[redacted]/a");
        expect(urlWithoutUserinfo("https://example.org/a@b")).toBe("https://example.org/a@b");
        expect(urlWithoutUserinfo("not-a-url")).toBe("not-a-url");
    });

    test("urlWithoutUserinfo removes the userinfo of urls nested in a url", () => {
        expect(urlWithoutUserinfo("https://example.org/a?next=ftp://user:secret@ftp.example.org")).toBe(
            "https://example.org/a?next=ftp://ftp.example.org",
        );
        expect(urlWithoutUserinfo("https://example.org/a?next=ftp://user:se?cret@ftp.example.org")).toBe(
            "https://example.org/a?next=ftp://[redacted]",
        );
        expect(urlWithoutUserinfo("https://example.org/a#ftp://user:se#cret@ftp.example.org")).toBe(
            "https://example.org/a#ftp://[redacted]",
        );
        expect(urlWithoutUserinfo("https://u1:s1@example.org/proxy/ftp://u2:s2@ftp.example.org/b")).toBe(
            "https://example.org/proxy/ftp://ftp.example.org/b",
        );
    });

    test("urlWithoutUserinfo removes the userinfo after any run of slashes", () => {
        expect(urlWithoutUserinfo("https://example.org/a?next=//user:secret@ftp.example.org")).toBe(
            "https://example.org/a?next=//ftp.example.org",
        );
        expect(urlWithoutUserinfo("https://example.org/a?next=///user:secret@ftp.example.org")).toBe(
            "https://example.org/a?next=///ftp.example.org",
        );
        expect(urlWithoutUserinfo("https://example.org/a?next=ftp:///user:secret@ftp.example.org")).toBe(
            "https://example.org/a?next=ftp:///ftp.example.org",
        );
        expect(urlWithoutUserinfo("https:///user:secret@example.org")).toBe("https:///example.org");
        expect(urlWithoutUserinfo("file:///data/a.bed")).toBe("file:///data/a.bed");
        expect(urlWithoutUserinfo("https://example.org/dir/user@file.txt")).toBe(
            "https://example.org/dir/user@file.txt",
        );
        // A "//" in a path starts an authority too, so a segment after it loses the part up to its "@".
        expect(urlWithoutUserinfo("https://example.org/a//b@c.txt")).toBe("https://example.org/a//c.txt");
    });

    test("extractNameFromUrl never falls back to a url with userinfo", () => {
        expect(extractNameFromUrl("https://user:secret@example.org/data/a.bed")).toBe("a.bed");
        expect(extractNameFromUrl("https://user:secret@example.org")).toBe("https://example.org");
        expect(extractNameFromUrl("https://user:secret@example.org/")).toBe("https://example.org/");
        expect(extractNameFromUrl("https://example.org?next=ftp://user:secret@ftp.example.org")).toBe(
            "https://example.org?next=ftp://ftp.example.org",
        );
        expect(extractNameFromUrl("https://example.org?next=//user:secret@ftp.example.org")).toBe(
            "https://example.org?next=//ftp.example.org",
        );
        expect(extractNameFromUrl("https:///user:secret@example.org")).toBe("https:///example.org");
    });

    test("extractNameFromUrl leaves out the userinfo of a url nested in the path", () => {
        expect(extractNameFromUrl("https://example.org/a?next=ftp://user:secret@ftp.example.org")).toBe("a");
        expect(extractNameFromUrl("https://example.org/proxy/ftp://user:secret@ftp.example.org")).toBe(
            "ftp.example.org",
        );
        expect(extractNameFromUrl("https://example.org/proxy//user:secret@ftp.example.org")).toBe("ftp.example.org");
    });

    test("extractNameFromUrl leaves out the userinfo of a percent-encoded url in the path", () => {
        expect(extractNameFromUrl("https://example.org/ftp%3A%2F%2Fu%3Asecret%40inner")).toBe("ftp://inner");
        expect(extractNameFromUrl("https://example.org/a/%2F%2Fu%3Asecret%40inner%2Fb.bed")).toBe("//inner/b.bed");
    });

    test.each([
        "https://example.org?x=1",
        "https://example.org:8080?x=1#f",
        "https://example.org:?x=1",
        "https://[::1]:8080#f",
        "https://example.org/a?email=alice@other.org",
        "https://example.org/#alice@other.org",
        "https://example.org/a?next=//example.com/b?email=alice@other.org",
    ])("urlWithoutUserinfo keeps %s without userinfo", (url) => {
        expect(urlWithoutUserinfo(url)).toBe(url);
    });

    test("urlWithoutUserinfo removes the userinfo before a query", () => {
        expect(urlWithoutUserinfo("https://user:secret@example.org?x=1")).toBe("https://example.org?x=1");
    });

    test.each([
        ["https://u:12?34@example.org", "https://[redacted]"],
        ["https://u:12#34@example.org", "https://[redacted]"],
        ["https://u:?34@example.org", "https://[redacted]"],
        ["https://u:12?34@example.org/a.bed", "https://[redacted]/a.bed"],
        ["https://to?ken@example.org", "https://[redacted]"],
        ["https://to#ken@example.org/a.bed", "https://[redacted]/a.bed"],
        ["https://user.name:12?a=b@example.org", "https://[redacted]"],
        ["https://alice@corp.org:pa?ss@example.org", "https://[redacted]"],
        ["https://example.org/a?next=//u:12?34@inner.example.org", "https://example.org/a?next=//[redacted]"],
        // The same shape without userinfo is redacted too, as no reading is safe for both.
        ["https://example.org?email=alice@other.org", "https://[redacted]"],
        ["https://example.org:?email=alice@other.org", "https://[redacted]"],
        ["https://example.org#alice@other.org", "https://[redacted]"],
        ["https://user:secret@example.org?email=alice@other.org", "https://[redacted]"],
    ])("urlWithoutUserinfo redacts the ambiguous authority of %s", (url, expected) => {
        expect(urlWithoutUserinfo(url)).toBe(expected);
    });

    test("extractNameFromUrl falls back to a url with its ambiguous authority redacted", () => {
        expect(extractNameFromUrl("https://u:12?34@example.org")).toBe("https://[redacted]");
        expect(extractNameFromUrl("https://example.org?email=alice@other.org")).toBe("https://[redacted]");
    });
});

// Each secret holds one of these characters, which the URLs around it never hold, so a match is a leak.
const SECRET_MARKERS = "ZQK0123456789";
const SECRET_ALPHABET = `${SECRET_MARKERS}?#=.:@`;
const SECRET_URL_FORMS = [
    (user, password) => `https://${user}:${password}@example.org`,
    (user, password) => `https://${user}:${password}@example.org/a.bed`,
    (user, password) => `https://${user}:${password}@example.org?x=y`,
    (user, password) => `https://${user}:${password}@example.org#f`,
    (user, password) => `https://${user}@${password}@example.org/a.bed?x=y`,
    (user, password) => `https://example.org/a?next=//${user}:${password}@inner.example.org/b`,
    (user, password) => `https://example.org/a?next=ftp://${user}:${password}@inner.example.org`,
];

// Seeded mulberry32, so a failure reproduces.
function seededRandom(seed) {
    let state = seed;
    return () => {
        state = (state + 0x6d2b79f5) | 0;
        let t = Math.imul(state ^ (state >>> 15), 1 | state);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

function randomSecret(random) {
    const pick = (chars) => chars[Math.floor(random() * chars.length)];
    let secret = "";
    const length = 3 + Math.floor(random() * 8);
    for (let i = 0; i < length; i++) {
        secret += pick(SECRET_ALPHABET);
    }
    return [...secret].some((char) => SECRET_MARKERS.includes(char)) ? secret : secret + pick(SECRET_MARKERS);
}

describe("url userinfo removal on random userinfo", () => {
    test("never echoes the user or password", () => {
        const random = seededRandom(20261123);
        for (let i = 0; i < 5000; i++) {
            const user = randomSecret(random);
            const password = randomSecret(random);
            const url = SECRET_URL_FORMS[Math.floor(random() * SECRET_URL_FORMS.length)](user, password);
            for (const output of [urlWithoutUserinfo(url), extractNameFromUrl(url)]) {
                for (const secret of [user, password]) {
                    expect(output.includes(secret), `${secret} of ${url} in ${output}`).toBe(false);
                }
            }
        }
    });
});
