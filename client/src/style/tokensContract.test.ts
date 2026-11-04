import { readFileSync } from "fs";
import { resolve } from "path";
import { describe, expect, it } from "vitest";

import { parseCustomProperties, readTokenSources, resolveToken } from "../../packages/ui/scripts/generateTokens.mjs";

// Semantic tokens that copy a Bootstrap theme color. warning is left out: orange-600
// is the nearest palette shade, not $brand-warning itself.
const BOOTSTRAP_BRAND_TOKENS = {
    primary: "--color-primary",
    secondary: "--color-secondary",
    success: "--color-success",
    info: "--color-info",
    danger: "--color-danger",
    dark: "--color-foreground",
};

/**
 * The client gets its design tokens from galaxy-ui's tokens.css, loaded by the
 * analysis entry. custom_theme_variables.scss only adds app-level tokens; a
 * redeclared package token would be a second copy that can drift.
 */
describe("client design tokens", () => {
    const packageTokens = parseCustomProperties(readTokenSources().tokens);

    it("does not redeclare galaxy-ui tokens in custom_theme_variables.scss", () => {
        const clientTokens = parseCustomProperties(
            readFileSync(resolve(__dirname, "scss/custom_theme_variables.scss"), "utf8"),
        );
        expect([...clientTokens.keys()].filter((name) => packageTokens.has(name))).toEqual([]);
    });

    it("keeps semantic colors equal to the Bootstrap theme they copy", () => {
        const blueTheme = readFileSync(resolve(__dirname, "scss/theme/blue.scss"), "utf8");
        const brand = new Map(
            [...blueTheme.matchAll(/^\$brand-([\w-]+):\s*(#[0-9a-f]{6});/gim)].map((match) => [
                match[1] as string,
                (match[2] as string).toLowerCase(),
            ]),
        );
        for (const [brandName, token] of Object.entries(BOOTSTRAP_BRAND_TOKENS)) {
            expect(resolveToken(packageTokens, token), `$brand-${brandName}`).toBe(brand.get(brandName));
        }
    });

    it("loads galaxy-ui's tokens in the analysis entry", () => {
        const entry = readFileSync(resolve(__dirname, "../entry/analysis/index.ts"), "utf8");
        expect(entry).toContain('import "@galaxyproject/galaxy-ui/tokens.css";');
    });
});
