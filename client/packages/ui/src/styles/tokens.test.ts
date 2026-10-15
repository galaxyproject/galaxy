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

// WCAG 2.x contrast ratio between two #rrggbb colors.
function contrast(first: string, second: string): number {
    const luminance = (hex: string) =>
        [1, 3, 5]
            .map((offset) => parseInt(hex.slice(offset, offset + 2), 16) / 255)
            .map((channel) => (channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4))
            .reduce((sum, channel, index) => sum + channel * ([0.2126, 0.7152, 0.0722][index] as number), 0);
    const [lighter, darker] = [luminance(first), luminance(second)].sort((a, b) => b - a) as [number, number];
    return (lighter + 0.05) / (darker + 0.05);
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

    it("gives every X / X-foreground pair at least 4.5:1 contrast (WCAG 1.4.3)", () => {
        const failures = SEMANTIC_COLORS.filter((name) => SEMANTIC_COLORS.includes(`${name}-foreground`))
            .map((name) => ({
                name,
                ratio: contrast(resolveToken(`--color-${name}`), resolveToken(`--color-${name}-foreground`)),
            }))
            .filter(({ ratio }) => ratio < 4.5)
            .map(({ name, ratio }) => `${name}-foreground on ${name}: ${ratio.toFixed(2)}:1`);
        expect(failures).toEqual([]);
    });

    it("gives input borders at least 3:1 against the background (WCAG 1.4.11)", () => {
        expect(contrast(resolveToken("--color-input"), resolveToken("--color-background"))).toBeGreaterThanOrEqual(3);
    });
});
