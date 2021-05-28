// Separated these functions from Util so we don't continue to load jquery every time somebody wants
// to format a disk size

/**
 * Round floaing point 'number' to 'numPlaces' number of decimal places.
 * @param{Object}   number      a floaing point number
 * @param{Object}   numPlaces   number of decimal places
 */
function roundToDecimalPlaces(number, numPlaces) {
    var placesMultiplier = 1;
    for (var i = 0; i < numPlaces; i++) {
        placesMultiplier *= 10;
    }
    return Math.round(number * placesMultiplier) / placesMultiplier;
}

// calculate on import
var kb = 1024;
var mb = kb * kb;
var gb = mb * kb;
var tb = gb * kb;

/**
 * Format byte size to string with units
 * @param{Integer}   size           - Size in bytes
 * @param{Boolean}   normal_font    - Switches font between normal and bold
 */
export function bytesToString(size, numberPlaces = 1) {
    // identify unit
    var unit = "";
    if (size >= tb) {
        size = size / tb;
        unit = "TB";
    } else if (size >= gb) {
        size = size / gb;
        unit = "GB";
    } else if (size >= mb) {
        size = size / mb;
        unit = "MB";
    } else if (size >= kb) {
        size = size / kb;
        unit = "KB";
    } else if (size > 0) {
        unit = "b";
    } else {
        return "-";
    }
    // return formatted string
    var rounded = unit == "b" ? size : roundToDecimalPlaces(size, numberPlaces);
    return `${rounded} ${unit}`;
}
