import { readFileSync } from "fs";
import { resolve } from "path";
import { describe, expect, it } from "vitest";

/**
 * The galaxy-ui package ships its token contract as tokens.css for external
 * consumers, while the client declares the same values (plus app-level extras)
 * in custom_theme_variables.scss. Every token the package declares must exist
 * in the client file with an identical value, so the two cannot drift.
 */
function parseCustomProperties(source: string): Map<string, string> {
    const properties = new Map<string, string>();
    for (const match of source.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
        properties.set(match[1] as string, (match[2] as string).trim());
    }
    return properties;
}

describe("galaxy-ui token contract", () => {
    const packageTokens = parseCustomProperties(
        readFileSync(resolve(__dirname, "../../packages/ui/src/styles/tokens.css"), "utf8"),
    );
    const clientTokens = parseCustomProperties(
        readFileSync(resolve(__dirname, "scss/custom_theme_variables.scss"), "utf8"),
    );

    it("declares a non-trivial token set", () => {
        expect(packageTokens.size).toBeGreaterThan(50);
    });

    it("matches the client's values for every token it declares", () => {
        const mismatches: string[] = [];
        for (const [name, value] of packageTokens) {
            const clientValue = clientTokens.get(name);
            if (clientValue !== value) {
                mismatches.push(`${name}: package="${value}" client="${clientValue ?? "<missing>"}"`);
            }
        }
        expect(mismatches).toEqual([]);
    });
});
