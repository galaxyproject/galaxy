import { readFileSync } from "fs";
import { resolve } from "path";
import { describe, expect, it } from "vitest";

/**
 * GHeading renders its size as an `h-*` class. The client also declares those
 * classes as global utilities in ui.scss, computed from the theme's Bootstrap
 * scale, but the package cannot reach app SCSS -- so it carries the same sizes
 * itself, and a consumer loading only the package still gets real headings.
 *
 * Two copies of one scale drift silently: change $font-size-base and the
 * utilities move while the component does not, leaving a GHeading a different
 * size from an `h-md` written by hand. This pins them together.
 */
const THEME = resolve(__dirname, "scss/theme/blue.scss");
const UTILITIES = resolve(__dirname, "scss/ui.scss");
const G_HEADING = resolve(__dirname, "../../packages/ui/src/components/GHeading.vue");

/** Resolve `$font-size-base` and the `$hN-font-size: $font-size-base * X` scale it drives. */
function themeFontSizes(): Map<string, string> {
    const source = readFileSync(THEME, "utf-8");
    const base = source.match(/\$font-size-base:\s*([\d.]+)rem/);
    expect(base, "theme no longer declares $font-size-base in rem").toBeTruthy();
    const baseRem = Number(base![1]);

    const sizes = new Map<string, string>([["$font-size-base", `${baseRem}rem`]]);
    for (const match of source.matchAll(/\$(h[1-6]-font-size):\s*\$font-size-base\s*\*\s*([\d.]+)/g)) {
        // toFixed(4) then trimmed: 0.85 * 1.75 is 1.4874999... in binary floating point.
        const value = Number((baseRem * Number(match[2])).toFixed(4));
        sizes.set(`$${match[1]}`, `${value}rem`);
    }
    return sizes;
}

/** Map each `.h-*` utility to the SCSS variable it is declared from. */
function utilityVariables(): Map<string, string> {
    const source = readFileSync(UTILITIES, "utf-8");
    const variables = new Map<string, string>();
    for (const match of source.matchAll(/\.(h-[a-z]+)\s*\{\s*font-size:\s*(\$[\w-]+);/g)) {
        variables.set(match[1] as string, match[2] as string);
    }
    return variables;
}

/** Map each `.h-*` rule in GHeading to its literal size. */
function componentSizes(): Map<string, string> {
    const source = readFileSync(G_HEADING, "utf-8");
    const sizes = new Map<string, string>();
    for (const match of source.matchAll(/\.(h-[a-z]+)\s*\{\s*font-size:\s*([\d.]+rem);/g)) {
        sizes.set(match[1] as string, match[2] as string);
    }
    return sizes;
}

describe("GHeading's size scale", () => {
    const theme = themeFontSizes();
    const utilities = utilityVariables();
    const component = componentSizes();

    it("finds the scale on both sides", () => {
        // Any of these coming back empty would make the comparison vacuous.
        expect(theme.size).toBeGreaterThan(1);
        expect(utilities.size).toBeGreaterThan(1);
        expect(component.size).toBeGreaterThan(1);
    });

    it("styles every size the client declares a utility for", () => {
        expect([...component.keys()].sort()).toEqual([...utilities.keys()].sort());
    });

    it("matches the value each utility resolves to", () => {
        const mismatches: string[] = [];
        for (const [utility, variable] of utilities) {
            const expected = theme.get(variable);
            if (expected === undefined) {
                mismatches.push(`${utility}: client uses ${variable}, which the theme no longer defines`);
            } else if (component.get(utility) !== expected) {
                mismatches.push(`${utility}: package=${component.get(utility)} theme=${expected} (${variable})`);
            }
        }
        expect(mismatches).toEqual([]);
    });
});
