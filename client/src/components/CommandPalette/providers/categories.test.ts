import { describe, expect, it } from "vitest";

import { makeCtx } from "../test-utils";
import { ALL_CATEGORY, availableCategories, categoryProviderId, PALETTE_CATEGORIES } from "./categories";
import { paletteProviders } from "./index";

describe("PALETTE_CATEGORIES", () => {
    it("names a registered provider for every category", () => {
        const providerIds = paletteProviders.map((provider) => provider.id);
        PALETTE_CATEGORIES.forEach((category) => expect(providerIds).toContain(categoryProviderId(category)));
    });

    it("leaves the actions provider to the 'All' fan-out", () => {
        expect(PALETTE_CATEGORIES.map(categoryProviderId)).not.toContain("actions");
    });

    it("gives every category a scope to borrow", () => {
        PALETTE_CATEGORIES.forEach((category) => expect(category.scope).toBeDefined());
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
        const categories = availableCategories(makeCtx({ isAnonymous: true }));
        expect(categories.map((category) => category.id)).toEqual(["all", "tools", "navigation"]);
    });

    it("hides the navigation category through its scope once its provider is disabled", () => {
        const ctx = makeCtx({ config: { command_palette_disabled_providers: ["navigation"] } });
        expect(availableCategories(ctx).map((category) => category.id)).not.toContain("navigation");
    });

    it("hides a scoped category once its provider is disabled", () => {
        const ctx = makeCtx({ config: { command_palette_disabled_providers: ["workflows", "tools"] } });
        const ids = availableCategories(ctx).map((category) => category.id);
        expect(ids).not.toContain("workflows");
        expect(ids).not.toContain("tools");
        expect(ids).toContain("histories");
    });
});
