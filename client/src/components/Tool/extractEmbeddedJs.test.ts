import { extractEmbeddedJs } from "./extractEmbeddedJs"; // Adjust the path as needed

describe("extractEmbeddedJs", () => {
    it("should extract single JavaScript fragment", () => {
        const input = "Text before $(simple) text after.";
        const result = extractEmbeddedJs(input);
        expect(result).toEqual([{ fragment: "$(simple)", start: 12 }]);
    });

    it("should extract multiple JavaScript fragments", () => {
        const input = "Text $(first) middle $(second) end.";
        const result = extractEmbeddedJs(input);
        expect(result).toEqual([
            { fragment: "$(first)", start: 5 },
            { fragment: "$(second)", start: 21 },
        ]);
    });

    it("should handle nested JavaScript fragments", () => {
        const input = "$(function() { return $(nested); })";
        const result = extractEmbeddedJs(input);
        expect(result).toEqual([{ fragment: "$(function() { return $(nested); })", start: 0 }]);
    });

    it("should handle text without embedded JavaScript", () => {
        const input = "This has no embedded JavaScript.";
        const result = extractEmbeddedJs(input);
        expect(result).toEqual([]);
    });

    it("should handle multiple nested fragments", () => {
        const input = "$(outer($(inner))) $(another)";
        const result = extractEmbeddedJs(input);
        expect(result).toEqual([
            { fragment: "$(outer($(inner)))", start: 0 },
            { fragment: "$(another)", start: 19 },
        ]);
    });

    it("should handle incomplete fragments gracefully", () => {
        const input = "Some text $(incomplete";
        const result = extractEmbeddedJs(input);
        expect(result).toEqual([]);
    });
});
