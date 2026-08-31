import { describe, expect, it } from "vitest";

import type { PaletteContext } from "../types";
import { ALL_CATEGORY, availableCategories, categoryScope, PALETTE_CATEGORIES } from "./categories";
import { paletteProviders } from "./index";

function makeCtx(overrides: Partial<PaletteContext> = {}): PaletteContext {
    return { canUseUnprivilegedTools: false, config: {}, isAdmin: false, isAnonymous: false, ...overrides };
}

describe("PALETTE_CATEGORIES", () => {
    it("names a registered provider for every category", () => {
        const providerIds = paletteProviders.map((provider) => provider.id);
        PALETTE_CATEGORIES.forEach((category) => expect(providerIds).toContain(category.providerId));
    });

    it("leaves the actions provider to the 'All' fan-out", () => {
        expect(PALETTE_CATEGORIES.map((category) => category.providerId)).not.toContain("actions");
    });

    it("resolves the scope every scoped category borrows", () => {
        PALETTE_CATEGORIES.filter((category) => category.scopeKey).forEach((category) => {
            expect(categoryScope(category)?.providerId).toBe(category.providerId);
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
