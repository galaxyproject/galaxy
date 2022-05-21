import { hashFnv32a } from "utils/utils";

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
 * Converts an HSL color value to RGB. Conversion formula
 * adapted from http://en.wikipedia.org/wiki/HSL_color_space.
 * Assumes h, s, and l are contained in the set [0, 1] and
 * returns r, g, and b in the set [0, 1].
 *
 * @param   {number}  h       The hue
 * @param   {number}  s       The saturation
 * @param   {number}  l       The lightness
 * @return  {Array}           The RGB representation
 */
export function hslToRgb(h, s, l) {
    var r;
    var g;
    var b;

    if (s == 0) {
        r = g = b = l; // achromatic
    } else {
        var hue2rgb = function hue2rgb(p, q, t) {
            if (t < 0) {
                t += 1;
            }
            if (t > 1) {
                t -= 1;
            }
            if (t < 1 / 6) {
                return p + (q - p) * 6 * t;
            }
            if (t < 1 / 2) {
                return q;
            }
            if (t < 2 / 3) {
                return p + (q - p) * (2 / 3 - t) * 6;
            }
            return p;
        };

        var q = l < 0.5 ? l * (1 + s) : l + s - l * s;
        var p = 2 * l - q;
        r = hue2rgb(p, q, h + 1 / 3);
        g = hue2rgb(p, q, h);
        b = hue2rgb(p, q, h - 1 / 3);
    }

    return [r, g, b];
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

    const primary = `hsl(${hue}, 100%, ${lightness}%)`;
    const darker = `hsl(${hue}, 100%, ${lightness - 40}%)`;
    const [r, g, b] = hslToRgb(hue, 1.0, lightness / 100);
    const contrasting = contrastingColor(r, g, b);

    return { primary, darker, contrasting };
}
