import { describe, expect, it } from "vitest";

import { makeCtx } from "../test-utils";
import type { PaletteContext } from "../types";
import { ALL_CATEGORY, availableCategories, categoryProviderId, PALETTE_CATEGORIES } from "./categories";
import { paletteProviders } from "./index";

function categoryIds(ctx: PaletteContext) {
    return availableCategories(ctx).map((category) => category.id);
}

describe("PALETTE_CATEGORIES", () => {
    it.each(PALETTE_CATEGORIES)("names a registered provider for the $label category", (category) => {
        const providerIds = paletteProviders.map((provider) => provider.id);

        expect(providerIds).toContain(categoryProviderId(category));
    });

    it("leaves the actions provider to the 'All' fan-out", () => {
        expect(PALETTE_CATEGORIES.map(categoryProviderId)).not.toContain("actions");
    });

    it.each(PALETTE_CATEGORIES)("gives the $label category a scope to borrow", (category) => {
        expect(category.scope).toBeDefined();
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
            "Reports",
            "Tools",
            "Navigation",
        ]);
    });

    it("hides the categories whose scope needs a login", () => {
        expect(categoryIds(makeCtx({ isAnonymous: true }))).toEqual(["all", "tools", "navigation"]);
    });

    it("hides the navigation category through its scope once its provider is disabled", () => {
        const ctx = makeCtx({ config: { command_palette_disabled_providers: ["navigation"] } });

        expect(categoryIds(ctx)).not.toContain("navigation");
    });

    it("hides a scoped category once its provider is disabled", () => {
        const ctx = makeCtx({ config: { command_palette_disabled_providers: ["workflows", "tools"] } });

        const ids = categoryIds(ctx);
        expect(ids).not.toContain("workflows");
        expect(ids).not.toContain("tools");
        expect(ids).toContain("histories");
    });
});
