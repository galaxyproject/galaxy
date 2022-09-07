import { hashFnv32a } from "utils/utils";
import { hsluvToRgb, hsluvToHex } from "hsluv";

/**
 * Implement W3C contrasting color algorithm
 * http://www.w3.org/TR/AERT#color-contrast
 *
 * @param   {number}  r       Red
 * @param   {number}  g       Green
 * @param   {number}  b       Blue
 * @return  {string}          Either 'white' or 'black'
 *
 * Assumes r, g, b are in the set [0, 1]
 */
export function contrastingColor(r, g, b) {
    var o = (r * 255 * 299 + g * 255 * 587 + b * 255 * 114) / 1000;
    return o > 125 ? "black" : "white";
}

/**
 * Simple 3-color keyed color scheme generated
 * from a string key
 */
export function keyedColorScheme(strKey) {
    const hash = hashFnv32a(strKey);
    const hue = Math.abs((hash >> 4) % 360);
    const lightnessOffset = 75;
    const lightness = lightnessOffset + (hash & 0xf);

    const [r, g, b] = hsluvToRgb([hue, 100, lightness]);
    const primary = `rgb(${r * 255},${g * 255},${b * 255})`;
    const darker = hsluvToHex([hue, 100, lightness - 20]);
    const contrasting = contrastingColor(r, g, b);

    return { primary, darker, contrasting };
}
