import { describe, expect, it } from "vitest";

import { resolveTheme, type Themes } from "./resolveTheme";

const THEMES: Themes = {
    blue: { "--masthead-color": "#2c3143" },
    orbit: { "--masthead-color": "#2c3143", "--content-background": "#2c3143", "--content-text": "#f0f2f8" },
};

describe("resolveTheme — embedded", () => {
    it("applies the theme requested via ?theme= when it exists", () => {
        const theme = resolveTheme({ embedded: true, themes: THEMES, queryTheme: "orbit" });
        expect(theme).toBe(THEMES.orbit);
        expect(theme?.["--content-background"]).toBe("#2c3143");
    });

    it("returns null for an unknown ?theme= id (no theme applied)", () => {
        expect(resolveTheme({ embedded: true, themes: THEMES, queryTheme: "nope" })).toBeNull();
    });

    it("returns null when embedded with no ?theme= (today's behavior)", () => {
        expect(resolveTheme({ embedded: true, themes: THEMES, queryTheme: undefined })).toBeNull();
    });

    it("ignores the user's currentTheme while embedded (only ?theme= selects)", () => {
        expect(
            resolveTheme({ embedded: true, themes: THEMES, queryTheme: undefined, currentTheme: "blue" }),
        ).toBeNull();
    });

    it("takes the first value when vue-router yields a string[] query", () => {
        const theme = resolveTheme({ embedded: true, themes: THEMES, queryTheme: ["orbit", "blue"] });
        expect(theme).toBe(THEMES.orbit);
    });
});

describe("resolveTheme — normal app", () => {
    it("applies the user's currentTheme when configured", () => {
        // A ?theme= query must NOT override the logged-in user's pref outside embed.
        const theme = resolveTheme({ embedded: false, themes: THEMES, queryTheme: "orbit", currentTheme: "blue" });
        expect(theme).toBe(THEMES.blue);
    });

    it("falls back to the first theme when currentTheme is unknown", () => {
        expect(resolveTheme({ embedded: false, themes: THEMES, currentTheme: "missing" })).toBe(THEMES.blue);
    });

    it("returns null when no themes are configured", () => {
        expect(resolveTheme({ embedded: false, themes: {}, currentTheme: "blue" })).toBeNull();
        expect(resolveTheme({ embedded: false, themes: null })).toBeNull();
    });
});
