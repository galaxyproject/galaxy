import { describe, expect, it } from "vitest";

import { generateTokens, readTokenSources } from "../../scripts/generateTokens.mjs";

const { theme: themeSource, tokens: tokensSource } = readTokenSources();

function parseCustomProperties(source: string): Map<string, string> {
    const properties = new Map<string, string>();
    for (const match of source.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
        properties.set(match[1] as string, (match[2] as string).trim());
    }
    return properties;
}

const tokens = parseCustomProperties(themeSource);

const COLOR_FAMILIES = ["blue", "grey", "green", "yellow", "orange", "red"];
const COLOR_SHADES = [100, 200, 300, 400, 500, 600, 700, 800, 900];

describe("galaxy-ui design tokens", () => {
    it("ships a tokens.css generated from the current theme.css", () => {
        // Regenerate with `pnpm --filter @galaxyproject/galaxy-ui build:tokens`.
        expect(tokensSource).toEqual(generateTokens(themeSource));
    });

    it("declares every shade of every color family as a literal", () => {
        // GButton builds selectors as var(--color-#{$color}-600) over the family
        // list, so a missing shade silently renders an unstyled variant.
        for (const family of COLOR_FAMILIES) {
            for (const shade of COLOR_SHADES) {
                expect(tokens.get(`--color-${family}-${shade}`)).toMatch(/^#[0-9a-f]{6}$/);
            }
        }
    });
});
