export const COMMON_FILTERS = {
    illumina: ["_1", "_2"],
    Rs: ["_R1", "_R2"],
    dot12s: [".1.fastq", ".2.fastq"],
};
export type CommonFiltersType = keyof typeof COMMON_FILTERS;
export const DEFAULT_FILTER: CommonFiltersType = "illumina";

interface HasName {
    name: string | null;
}

export function guessInitialFilterType(elements: HasName[]): CommonFiltersType | null {
    let illumina = 0;
    let dot12s = 0;
    let Rs = 0;

    //should we limit the forEach? What if there are 1000s of elements?
    elements.forEach((element) => {
        if (element.name?.includes(".1.fastq") || element.name?.includes(".2.fastq")) {
            dot12s++;
        } else if (element.name?.includes("_R1") || element.name?.includes("_R2")) {
            Rs++;
        } else if (element.name?.includes("_1") || element.name?.includes("_2")) {
            illumina++;
        }
    });
    // if we cannot filter don't set an initial filter and hide all the data
    if (illumina == 0 && dot12s == 0 && Rs == 0) {
        return null;
    } else if (illumina > dot12s && illumina > Rs) {
        return "illumina";
    } else if (dot12s > illumina && dot12s > Rs) {
        return "dot12s";
    } else if (Rs > illumina && Rs > dot12s) {
        return "Rs";
    } else {
        return "illumina";
    }
}

function _defaultName(fwd: HasName, rev: HasName): string {
    return fwd.name + "_and_" + rev.name;
}

export function guessNameForPair(
    fwd: HasName,
    rev: HasName,
    forwardFilter: string,
    reverseFilter: string,
    willRemoveExtensions: boolean
) {
    let fwdName = fwd.name;
    let revName = rev.name;
    const fwdNameFilter = fwdName?.replace(new RegExp(forwardFilter || ""), "");
    const revNameFilter = revName?.replace(new RegExp(reverseFilter || ""), "");
    if (!fwdNameFilter || !revNameFilter || !fwdName || !revName) {
        return _defaultName(fwd, rev);
    }
    let lcs = naiveStartingAndEndingLCS(fwdNameFilter, revNameFilter);
    // remove url prefix if files were uploaded by url
    const lastSlashIndex = lcs.lastIndexOf("/");
    if (lastSlashIndex > 0) {
        const urlprefix = lcs.slice(0, lastSlashIndex + 1);
        lcs = lcs.replace(urlprefix, "");
    }

    if (willRemoveExtensions) {
        const lastDotIndex = lcs.lastIndexOf(".");
        if (lastDotIndex > 0) {
            const extension = lcs.slice(lastDotIndex, lcs.length);
            lcs = lcs.replace(extension, "");
            fwdName = fwdName.replace(extension, "");
            revName = revName.replace(extension, "");
        }
    }
    if (lcs.endsWith(".") || lcs.endsWith("_")) {
        lcs = lcs.substring(0, lcs.length - 1);
    }
    return _defaultName(fwd, rev);
}

/** Return the concat'd longest common prefix and suffix from two strings */
export function naiveStartingAndEndingLCS(s1: string, s2: string) {
    let fwdLCS = "";
    let revLCS = "";
    let i = 0;
    let j = 0;
    while (i < s1.length && i < s2.length) {
        if (s1[i] !== s2[i]) {
            break;
        }
        fwdLCS += s1[i];
        i += 1;
    }
    if (i === s1.length) {
        return s1;
    }
    if (i === s2.length) {
        return s2;
    }

    i = s1.length - 1;
    j = s2.length - 1;
    while (i >= 0 && j >= 0) {
        if (s1[i] !== s2[j]) {
            break;
        }
        revLCS = [s1[i], revLCS].join("");
        i -= 1;
        j -= 1;
    }
    return fwdLCS + revLCS;
}

export function createPair<T extends HasName>(fwd: T, rev: T, name: string): { forward: T; reverse: T; name: string } {
    // Ensure existence and don't pair something with itself
    if (!(fwd && rev) || fwd === rev) {
        throw new Error(`Bad pairing: ${[JSON.stringify(fwd), JSON.stringify(rev)]}`);
    }
    return { forward: fwd, reverse: rev, name: name };
}
