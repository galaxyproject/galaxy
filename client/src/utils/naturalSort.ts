// Alphanumeric/natural sort fn
export function naturalSort(a = "", b = ""): number {
    // setup temp-scope variables for comparison evauluation
    const re = /(-?[0-9.]+)/g;

    const x = a.toString().toLowerCase() || "";
    const y = b.toString().toLowerCase() || "";
    const nC = String.fromCharCode(0);
    const xN = x.replace(re, `${nC}$1${nC}`).split(nC);
    const yN = y.replace(re, `${nC}$1${nC}`).split(nC);
    const xD = new Date(x).getTime();
    const yD = xD ? new Date(y).getTime() : null;
    // natural sorting of dates
    if (yD) {
        if (xD < yD) {
            return -1;
        } else if (xD > yD) {
            return 1;
        }
    }

    // natural sorting through split numeric strings and default strings
    let oFxNcL;

    let oFyNcL;
    for (let cLoc = 0, numS = Math.max(xN.length, yN.length); cLoc < numS; cLoc++) {
        oFxNcL = parseFloat(xN[cLoc] || "") || xN[cLoc];
        oFyNcL = parseFloat(yN[cLoc] || "") || yN[cLoc];

        // Check if either part is undefined
        if (oFxNcL === undefined) {
            return -1;
        }
        if (oFyNcL === undefined) {
            return 1;
        }

        if (oFxNcL < oFyNcL) {
            return -1;
        } else if (oFxNcL > oFyNcL) {
            return 1;
        }
    }
    return 0;
}
