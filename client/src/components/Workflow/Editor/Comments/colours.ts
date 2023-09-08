import { hexToHsluv, hsluvToHex } from "hsluv";

export const colours = {
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

export type Colour = keyof typeof colours;

export const brightColours = (() => {
    const brighter: Record<string, string> = {};
    Object.entries(colours).forEach(([name, colour]) => {
        const hsluv = hexToHsluv(colour);
        let l = hsluv[2];
        l += (100 - l) * 0.5;
        hsluv[2] = l;
        brighter[name] = hsluvToHex(hsluv);
    });
    return brighter as Record<Colour, string>;
})();

export const brighterColours = (() => {
    const brighter: Record<string, string> = {};
    Object.entries(colours).forEach(([name, colour]) => {
        const hsluv = hexToHsluv(colour);
        let l = hsluv[2];
        l += (100 - l) * 0.95;
        hsluv[2] = l;
        brighter[name] = hsluvToHex(hsluv);
    });
    return brighter as Record<Colour, string>;
})();

export const darkenedColours = {
    ...colours,
    turquoise: "#00a6c0",
    lime: "#5eae00",
    yellow: "#e9ad00",
};
