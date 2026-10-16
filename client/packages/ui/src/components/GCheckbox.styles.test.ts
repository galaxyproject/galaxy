/// <reference types="vite/client" />
import { compileStyle, parse } from "@vue/compiler-sfc";
import { describe, expect, it } from "vitest";

import source from "./GCheckbox.vue?raw";

function compiledSelectors(): string[] {
    const filename = "GCheckbox.vue";
    const { descriptor } = parse(source, { filename });
    const selectors: string[] = [];
    for (const style of descriptor.styles) {
        const result = compileStyle({
            source: style.content,
            filename,
            id: "data-v-test",
            scoped: style.scoped,
            preprocessLang: style.lang as "scss",
        });
        expect(result.errors).toEqual([]);
        result.rawResult!.root.walkRules((rule) => {
            selectors.push(...rule.selectors);
        });
    }
    return selectors;
}

describe("GCheckbox styles", () => {
    // Scoped CSS puts the scope attribute on the last compound only, so a bare `.g-small` ancestor would match a modal or any other element
    it("ties every rule on the input to the checkbox's own root", () => {
        const inputSelectors = compiledSelectors().filter((selector) => selector.includes(".g-checkbox-input"));
        expect(inputSelectors.length).toBeGreaterThan(0);
        const rootAnchored = /^\.g-checkbox(?![\w-])[^\s>+~]*\s*>\s*\.g-checkbox-input\[data-v-test\]/;
        const leaking = inputSelectors.filter(
            (selector) => /[\s>+~]/.test(selector.trim()) && !rootAnchored.test(selector),
        );
        expect(leaking).toEqual([]);
    });
});
