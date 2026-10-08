import { describe, expect, it } from "vitest";

import { generateTokens, readTokenSources } from "../../scripts/generateTokens.mjs";

const { theme: themeSource, tokens: tokensSource, brandTokens: brandTokensSource } = readTokenSources();

function parseCustomProperties(source: string): Map<string, string> {
    const properties = new Map<string, string>();
    for (const match of source.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
        properties.set(match[1] as string, (match[2] as string).trim());
    }
    return properties;
}

const tokens = parseCustomProperties(themeSource);

function resolveToken(name: string, seen: string[] = []): string {
    const value = tokens.get(name);
    if (value === undefined) {
        throw new Error(`${[...seen, name].join(" -> ")}: not declared`);
    }
    const reference = value.match(/^var\((--[\w-]+)\)$/);
    return reference ? resolveToken(reference[1] as string, [...seen, name]) : value.toLowerCase();
}

const COLOR_FAMILIES = ["blue", "gray", "green", "yellow", "orange", "red"];
const COLOR_SHADES = [100, 200, 300, 400, 500, 600, 700, 800, 900];

// shadcn/ui's names plus Galaxy's additions; consumers (and later Tailwind
// utilities) rely on every one of these existing.
const SEMANTIC_COLORS = [
    "background",
    "foreground",
    "card",
    "card-foreground",
    "popover",
    "popover-foreground",
    "muted",
    "muted-foreground",
    "sidebar",
    "sidebar-foreground",
    "sidebar-primary",
    "sidebar-primary-foreground",
    "sidebar-accent",
    "sidebar-accent-foreground",
    "sidebar-border",
    "sidebar-ring",
    "accent",
    "accent-foreground",
    "selected",
    "selected-foreground",
    "primary",
    "primary-foreground",
    "secondary",
    "secondary-foreground",
    "highlight",
    "highlight-foreground",
    "inverse",
    "inverse-foreground",
    "success",
    "success-foreground",
    "info",
    "info-foreground",
    "warning",
    "warning-foreground",
    "danger",
    "danger-foreground",
    "border",
    "input",
    "ring",
];

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

    it("keeps every deprecated grey shade pointing at its gray shade", () => {
        for (const shade of COLOR_SHADES) {
            expect(tokens.get(`--color-grey-${shade}`)).toBe(`var(--color-gray-${shade})`);
        }
    });

    it("declares every semantic color, resolving to a palette value", () => {
        for (const name of SEMANTIC_COLORS) {
            expect(resolveToken(`--color-${name}`)).toMatch(/^#[0-9a-f]{6}$/);
        }
    });

    it("only references tokens it declares", () => {
        const dangling = [...tokens].flatMap(([name, value]) =>
            [...value.matchAll(/var\((--[\w-]+)\)/g)]
                .map((match) => match[1] as string)
                .filter((reference) => !tokens.has(reference))
                .map((reference) => `${name} -> ${reference}`),
        );
        expect(dangling).toEqual([]);
    });

    it("matches the Galaxy brand colors in @galaxyproject/brand-tokens", () => {
        const brand = parseCustomProperties(brandTokensSource);
        const brandColor = (name: string) => brand.get(name)?.toLowerCase();
        expect(resolveToken("--color-primary")).toBe(brandColor("--color-galaxy-primary"));
        expect(resolveToken("--color-foreground")).toBe(brandColor("--color-galaxy-dark"));
        expect(resolveToken("--color-highlight")).toBe(brandColor("--color-galaxy-gold"));
    });
});
