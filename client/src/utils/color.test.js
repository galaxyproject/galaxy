import { keyedColorScheme } from "utils/color";

describe("Color Utilities", () => {
    test("Test Color Scheme Generation", () => {
        const { primary, darker, dimmed } = keyedColorScheme("test");
        expect(primary).toBe("rgb(254,175,206)");
        expect(darker).toBe("#ff8cbd");
        expect(dimmed).toBe("#ff9ec5");
    });
});
