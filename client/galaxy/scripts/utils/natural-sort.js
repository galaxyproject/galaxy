// Alphanumeric/natural sort fn
function naturalSort(a, b) {
    // setup temp-scope variables for comparison evauluation
    var re = /(-?[0-9.]+)/g;

    var x = a.toString().toLowerCase() || "";
    var y = b.toString().toLowerCase() || "";
    var nC = String.fromCharCode(0);
    var xN = x.replace(re, `${nC}$1${nC}`).split(nC);
    var yN = y.replace(re, `${nC}$1${nC}`).split(nC);
    var xD = new Date(x).getTime();
    var yD = xD ? new Date(y).getTime() : null;
    // natural sorting of dates
    if (yD) {
        if (xD < yD) {
            return -1;
        } else if (xD > yD) {
            return 1;
        }
    }

    // natural sorting through split numeric strings and default strings
    var oFxNcL;

    var oFyNcL;
    for (var cLoc = 0, numS = Math.max(xN.length, yN.length); cLoc < numS; cLoc++) {
        oFxNcL = parseFloat(xN[cLoc]) || xN[cLoc];
        oFyNcL = parseFloat(yN[cLoc]) || yN[cLoc];
        if (oFxNcL < oFyNcL) {
            return -1;
        } else if (oFxNcL > oFyNcL) {
            return 1;
        }
    }
    return 0;
}

export default naturalSort;
