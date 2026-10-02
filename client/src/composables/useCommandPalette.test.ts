import { describe, expect, it } from "vitest";

import { useCommandPalette } from "./useCommandPalette";

describe("useCommandPalette", () => {
    it("shares the open state across all consumers", () => {
        const first = useCommandPalette();
        const second = useCommandPalette();

        expect(first.isPaletteOpen.value).toBe(false);

        first.openPalette();
        expect(second.isPaletteOpen.value).toBe(true);

        second.closePalette();
        expect(first.isPaletteOpen.value).toBe(false);

        first.togglePalette();
        expect(second.isPaletteOpen.value).toBe(true);
    });
});
