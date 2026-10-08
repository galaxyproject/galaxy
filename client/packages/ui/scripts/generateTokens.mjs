// Generates src/styles/tokens.css (plain `:root` custom properties) from the
// Tailwind `@theme` source in src/styles/theme.css, so the token names live in
// one file. Run via `pnpm --filter @galaxyproject/galaxy-ui build:tokens`.
import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const stylesDir = resolve(dirname(fileURLToPath(import.meta.url)), "../src/styles");
export const themePath = resolve(stylesDir, "theme.css");
export const tokensPath = resolve(stylesDir, "tokens.css");

const HEADER = `/*
 * GENERATED from theme.css by scripts/generateTokens.mjs -- do not edit.
 *
 * Consumers without Tailwind import this file so galaxy-ui components render
 * with real colors and spacing:
 *
 *     import "@galaxyproject/galaxy-ui/tokens.css";
 */
`;

export function generateTokens(themeSource) {
    const body = themeSource.slice(themeSource.indexOf("@theme"));
    if (!body.startsWith("@theme {")) {
        throw new Error("theme.css must contain a single `@theme {` block");
    }
    return HEADER + body.replace("@theme {", ":root,\n.reset-theme-variables {");
}

// The token tests read their sources through here: the package has no Node
// types to type-check fs against, and vitest empties CSS imports, even ?raw.
export function readTokenSources() {
    const brandTokensPath = createRequire(import.meta.url).resolve("@galaxyproject/brand-tokens/tokens.css");
    return {
        theme: readFileSync(themePath, "utf8"),
        tokens: readFileSync(tokensPath, "utf8"),
        brandTokens: readFileSync(brandTokensPath, "utf8"),
    };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
    writeFileSync(tokensPath, generateTokens(readFileSync(themePath, "utf8")));
}
