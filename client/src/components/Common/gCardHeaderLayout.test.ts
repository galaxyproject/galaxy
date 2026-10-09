import { describe, expect, it } from "vitest";

import { chooseHeaderLayout } from "./gCardHeaderLayout";

const base = { available: 300, gap: 4, titleMin: 160 };

describe("chooseHeaderLayout", () => {
    it("keeps one row when the header has no badges", () => {
        expect(chooseHeaderLayout({ ...base, actions: 400 })).toBe("inline");
    });

    it("keeps the badges beside the title while a 10rem title still fits", () => {
        // 20 + 4 + 160 + 4 + 64 + 4 + 44 = 300
        expect(chooseHeaderLayout({ ...base, select: 20, badges: 64, actions: 44 })).toBe("inline");
    });

    it("puts the badges under the actions when they only fit in the actions column", () => {
        // one row needs 301; the column is max(65, 44) = 65 wide and leaves the title 20 + 4 + 160 + 4 + 65 = 253
        expect(chooseHeaderLayout({ ...base, select: 20, badges: 65, actions: 44 })).toBe("column");
        // 20 + 4 + 160 + 4 + 112 = 300
        expect(chooseHeaderLayout({ ...base, select: 20, badges: 112, actions: 44 })).toBe("column");
    });

    it("gives the badges their own row when the actions column would squeeze the title", () => {
        expect(chooseHeaderLayout({ ...base, select: 20, badges: 113, actions: 44 })).toBe("stacked");
    });

    it("sizes the actions column by the wider of the badges and the actions", () => {
        // 160 + 4 + max(40, 136) = 300
        expect(chooseHeaderLayout({ ...base, badges: 40, actions: 136 })).toBe("column");
        expect(chooseHeaderLayout({ ...base, badges: 40, actions: 137 })).toBe("stacked");
    });

    it("never uses the actions column for a card without actions", () => {
        // 160 + 4 + 136 = 300
        expect(chooseHeaderLayout({ ...base, badges: 136 })).toBe("inline");
        expect(chooseHeaderLayout({ ...base, badges: 137 })).toBe("stacked");
    });
});
