import { hashFnv32a } from "utils/utils";
import { hsluvToRgb, hsluvToHex } from "hsluv";

/**
 * Simple 3-color keyed color scheme generated
 * from a string key
 */
export function keyedColorScheme(strKey) {
    const hash = hashFnv32a(strKey);
    const hue = Math.abs((hash >> 4) % 360);
    const lightnessOffset = 75;
    let lightness = lightnessOffset + (hash & 0xf);

    // randomly make yellow tags bright
    if (hue >= 70 && hue <= 95 && (hash & 0x100) === 0x100) {
        lightness += (100 - lightness) * 0.75;
    }

    const [r, g, b] = hsluvToRgb([hue, 100, lightness]);
    const primary = `rgb(${r * 255},${g * 255},${b * 255})`;
    const darker = hsluvToHex([hue, 100, lightness * 0.9]);
    const dimmed = hsluvToHex([hue, 100, lightness * 0.95]);

    return { primary, darker, dimmed };
}
