import { readFileSync } from "fs";
import { resolve } from "path";
import { describe, expect, it } from "vitest";

/**
 * The client gets its design tokens from galaxy-ui's tokens.css, loaded by the
 * analysis entry. custom_theme_variables.scss only adds app-level tokens; a
 * redeclared package token would be a second copy that can drift.
 */
function declaredProperties(source: string): string[] {
    return [...source.matchAll(/(--[\w-]+)\s*:/g)].map((match) => match[1] as string);
}

describe("client design tokens", () => {
    const packageTokens = new Set(
        declaredProperties(readFileSync(resolve(__dirname, "../../packages/ui/src/styles/tokens.css"), "utf8")),
    );

    it("does not redeclare galaxy-ui tokens in custom_theme_variables.scss", () => {
        const clientTokens = declaredProperties(
            readFileSync(resolve(__dirname, "scss/custom_theme_variables.scss"), "utf8"),
        );
        expect(clientTokens.filter((name) => packageTokens.has(name))).toEqual([]);
    });

    it("loads galaxy-ui's tokens in the analysis entry", () => {
        const entry = readFileSync(resolve(__dirname, "../entry/analysis/index.ts"), "utf8");
        expect(entry).toContain('import "@galaxyproject/galaxy-ui/tokens.css";');
    });
});
