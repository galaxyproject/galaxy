import { extractEmbeddedJs } from "./extractEmbeddedJs";

describe("extractEmbeddedJs", () => {
    it("should extract single JavaScript fragment", () => {
        const input = "Text before $(simple) text after.";
        const result = extractEmbeddedJs(input);
        expect(result).toEqual([{ fragment: "simple)", start: 14 }]);
    });

    it("should extract multiple JavaScript fragments", () => {
        const input = "Text $(first) middle $(second) end.";
        const result = extractEmbeddedJs(input);
        expect(result).toEqual([
            { fragment: "first)", start: 7 },
            { fragment: "second)", start: 23 },
        ]);
    });

    it("should handle nested JavaScript fragments", () => {
        const input = "$(function() { return $(nested); })";
        const result = extractEmbeddedJs(input);
        expect(result).toEqual([{ fragment: "function() { return $(nested); })", start: 2 }]);
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
            { fragment: "outer($(inner)))", start: 2 },
            { fragment: "another)", start: 21 },
        ]);
    });

    it("should handle incomplete fragments gracefully", () => {
        const input = "Some text $(incomplete";
        const result = extractEmbeddedJs(input);
        expect(result).toEqual([]);
    });

    it("should skip shell_command prefix", () => {
        const input = "shell_command: $(first)";
        const regex = /shell_command:\w+/;
        const result = extractEmbeddedJs(input, regex);
        expect(result).toEqual([{ fragment: "first)", start: 17 }]);
    });

    it("should skip shell_command prefix and stop at next line", () => {
        const input = "shell_command: $(first)\n$(second)";
        const regex = /shell_command:(.*)$/m;
        const result = extractEmbeddedJs(input, regex);
        expect(result).toEqual([{ fragment: "first)", start: 17 }]);
    });
});
