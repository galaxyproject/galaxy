import { Hsluv } from "hsluv";
import { hashFnv32a } from "utils/utils";

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

    const converter = new Hsluv();
    converter.hsluv_h = hue;
    converter.hsluv_s = 100;
    converter.hsluv_l = lightness;
    converter.hsluvToHex();
    const primary = `rgb(${parseInt(converter.rgb_r * 255)},${parseInt(converter.rgb_g * 255)},${parseInt(
        converter.rgb_b * 255
    )})`;
    converter.hsluv_l = lightness * 0.9;
    converter.hsluvToHex();
    const darker = converter.hex;
    converter.hsluv_l = lightness * 0.95;
    converter.hsluvToHex();
    const dimmed = converter.hex;
    return { primary, darker, dimmed };
}
