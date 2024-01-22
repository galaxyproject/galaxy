import { Hsluv } from "hsluv";

export const colors = {
    black: "#000",
    blue: "#004cec",
    turquoise: "#00bbd9",
    green: "#319400",
    lime: "#68c000",
    orange: "#f48400",
    yellow: "#fdbd0b",
    red: "#e31920",
    pink: "#fb00a6",
} as const;

export type Color = keyof typeof colors;
export type HexColor = `#${string}`;

export const brightColors = (() => {
    const brighter: Record<string, string> = {};
    const converter = new Hsluv();

    Object.entries(colors).forEach(([name, color]) => {
        converter.hex = color;
        converter.hexToHsluv();
        converter.hsluv_l += (100 - converter.hsluv_l) * 0.5;
        converter.hsluvToHex();
        brighter[name] = converter.hex;
    });
    return brighter as Record<Color, HexColor>;
})();

export const brighterColors = (() => {
    const brighter: Record<string, string> = {};
    const converter = new Hsluv();

    Object.entries(colors).forEach(([name, color]) => {
        converter.hex = color;
        converter.hexToHsluv();
        converter.hsluv_l += (100 - converter.hsluv_l) * 0.95;
        converter.hsluvToHex();
        brighter[name] = converter.hex;
    });
    return brighter as Record<Color, HexColor>;
})();

export const darkenedColors = {
    ...colors,
    turquoise: "#00a6c0" as const,
    lime: "#5eae00" as const,
    yellow: "#e9ad00" as const,
};
