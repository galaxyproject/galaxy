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

/** Values the client computes from SCSS variables cannot be compared as plain text. */
function isInterpolated(value: string): boolean {
    return value.includes("#{");
}

const COLOR_FAMILIES = ["blue", "green", "grey", "orange", "red", "yellow"];
const COLOR_SHADES = [100, 200, 300, 400, 500, 600, 700, 800, 900];
const NON_PALETTE_TOKENS = [
    "--background-color",
    "--font-size-large",
    "--font-size-medium",
    "--font-size-small",
    "--spacing",
    "--spacing-1",
    "--spacing-2",
    "--spacing-3",
    "--spacing-4",
    "--spacing-5",
    "--spacing-6",
    "--spacing-7",
    "--spacing-8",
];

describe("galaxy-ui token contract", () => {
    const packageTokens = parseCustomProperties(
        readFileSync(resolve(__dirname, "../../packages/ui/src/styles/tokens.css"), "utf8"),
    );
    const clientTokens = parseCustomProperties(
        readFileSync(resolve(__dirname, "scss/custom_theme_variables.scss"), "utf8"),
    );

    it("declares every shade of every color family", () => {
        // GButton builds selectors as var(--color-#{$color}-600) over the family
        // list, so a missing shade silently renders an unstyled variant.
        const expected = COLOR_FAMILIES.flatMap((family) => COLOR_SHADES.map((shade) => `--color-${family}-${shade}`));
        expect([...packageTokens.keys()].filter((name) => expected.includes(name)).sort()).toEqual(expected.sort());
    });

    it("declares exactly the non-palette tokens the contract promises", () => {
        const actual = [...packageTokens.keys()].filter((name) => !/^--color-[a-z]+-\d00$/.test(name)).sort();
        expect(actual).toEqual([...NON_PALETTE_TOKENS].sort());
    });

    it("ships literal values the client can be compared against", () => {
        const interpolated = [...packageTokens].filter(([, value]) => isInterpolated(value)).map(([name]) => name);
        expect(interpolated).toEqual([]);
    });

    it("matches the client's values for every token it declares", () => {
        const mismatches: string[] = [];
        for (const [name, value] of packageTokens) {
            const clientValue = clientTokens.get(name);
            if (clientValue === undefined) {
                mismatches.push(`${name}: declared by the package, missing from the client`);
            } else if (isInterpolated(clientValue)) {
                mismatches.push(
                    `${name}: the client computes this from an SCSS variable (${clientValue}), ` +
                        `so it cannot be part of the package's literal token contract`,
                );
            } else if (clientValue !== value) {
                mismatches.push(`${name}: package="${value}" client="${clientValue}"`);
            }
        }
        expect(mismatches).toEqual([]);
    });
});
