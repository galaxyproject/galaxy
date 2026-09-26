import { describe, expect, it } from "vitest";

import type { PaletteContext } from "../types";
import { ALL_CATEGORY, availableCategories, categoryProviderId, PALETTE_CATEGORIES } from "./categories";
import { paletteProviders } from "./index";

function makeCtx(overrides: Partial<PaletteContext> = {}): PaletteContext {
    return { canUseUnprivilegedTools: false, config: {}, isAnonymous: false, ...overrides };
}

describe("PALETTE_CATEGORIES", () => {
    it("names a registered provider for every category", () => {
        const providerIds = paletteProviders.map((provider) => provider.id);
        PALETTE_CATEGORIES.forEach((category) => expect(providerIds).toContain(categoryProviderId(category)));
    });

    it("leaves the actions provider to the 'All' fan-out", () => {
        expect(PALETTE_CATEGORIES.map(categoryProviderId)).not.toContain("actions");
    });

    it("gives every category either a scope or a provider of its own, never both", () => {
        PALETTE_CATEGORIES.forEach((category) => {
            expect(Boolean(category.scope) !== Boolean(category.providerId)).toBe(true);
        });
    });
});

describe("availableCategories", () => {
    it("offers 'All' first, then one category per provider", () => {
        const categories = availableCategories(makeCtx());
        expect(categories[0]).toBe(ALL_CATEGORY);
        expect(categories.map((category) => category.label)).toEqual([
            "All",
            "Workflows",
            "Histories",
            "Datasets",
            "Visualizations",
            "Invocations",
            "Pages",
            "Tools",
            "Navigation",
        ]);
    });

    it("hides the categories whose scope needs a login", () => {
        const categories = availableCategories(makeCtx({ isAnonymous: true }));
        expect(categories.map((category) => category.id)).toEqual(["all", "tools", "navigation"]);
    });
});
