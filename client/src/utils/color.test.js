import { describe, expect, it } from "vitest";

import { keyedColorScheme } from "@/utils/color";

describe("keyedColorScheme", () => {
    it('generates the expected primary, darker, and dimmed colors for "test"', () => {
        const { primary, darker, dimmed } = keyedColorScheme("test");
        expect(primary).toBe("rgb(254,175,206)");
        expect(darker).toBe("#ff8cbd");
        expect(dimmed).toBe("#ff9ec5");
    });
});
