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

export function _guessNameForPair(
    fwd: HasName,
    rev: HasName,
    forwardFilter: RegExp,
    reverseFilter: RegExp,
    willRemoveExtensions: boolean
) {
    let fwdName = fwd.name;
    let revName = rev.name;
    const fwdNameFilter = fwdName?.replace(forwardFilter, "");
    const revNameFilter = revName?.replace(reverseFilter, "");
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
    return lcs || _defaultName(fwd, rev);
}

export function guessNameForPair(
    fwd: HasName,
    rev: HasName,
    forwardFilter: string,
    reverseFilter: string,
    willRemoveExtensions: boolean
) {
    return _guessNameForPair(
        fwd,
        rev,
        new RegExp(forwardFilter || ""),
        new RegExp(reverseFilter || ""),
        willRemoveExtensions
    );
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

/* This abstraction describes scoring function to attempt to auto match pairs with. */
export type MatchingFunction = (params: {
    matchTo: string;
    possible: string;
    index: number;
    bestMatch: { score: number; index: number };
}) => { score: number; index: number };

export const matchOnlyIfExact: MatchingFunction = (params) => {
    params = params || {};
    if (params.matchTo === params.possible) {
        return {
            index: params.index,
            score: 1.0,
        };
    }
    return params.bestMatch;
};

export const matchOnPercentOfStartingAndEndingLCS: MatchingFunction = (params) => {
    params = params || {};
    const match = naiveStartingAndEndingLCS(params.matchTo, params.possible).length;
    const score = match / Math.max(params.matchTo.length, params.possible.length);
    if (score > params.bestMatch.score) {
        return {
            index: params.index,
            score: score,
        };
    }
    return params.bestMatch;
};

// take in a matching function and return a function that will take two lists
// and yield all the pairs, the PairedListCollectionBuilder did stuff with state
// deep in body of the function. This version just modifies the given lists and
// returns pairs
export function statelessAutoPairFnBuilder<T extends HasName>(
    match: MatchingFunction,
    scoreThreshold: number,
    forwardFilter: string,
    reverseFilter: string,
    willRemoveExtensions: boolean
) {
    function splicePairOutOfSuppliedLists(params: {
        listA: T[];
        indexA: number;
        listB: T[];
        indexB: number;
    }): { forward: T; reverse: T; name: string } | undefined {
        const a = params.listA.splice(params.indexA, 1)[0] as T;
        const b = params.listB.splice(params.indexB, 1)[0] as T;
        if (!a || !b) {
            return undefined;
        }
        const aInBIndex = params.listB.indexOf(a);
        const bInAIndex = params.listA.indexOf(b);
        if (aInBIndex !== -1) {
            params.listB.splice(aInBIndex, 1);
        }
        if (bInAIndex !== -1) {
            params.listA.splice(bInAIndex, 1);
        }
        const pairName = guessNameForPair(a, b, forwardFilter, reverseFilter, willRemoveExtensions);
        return createPair(a, b, pairName);
    }

    // compile these here outside of the loop
    const forwardRegExp = new RegExp(forwardFilter);
    const reverseRegExp = new RegExp(reverseFilter);

    function _preprocessMatch(params: {
        matchTo: T;
        possible: T;
        index: number;
        bestMatch: { score: number; index: number };
    }) {
        return Object.assign(params, {
            matchTo: params.matchTo.name?.replace(forwardRegExp || "", ""),
            possible: params.possible.name?.replace(reverseRegExp || "", ""),
            index: params.index,
            bestMatch: params.bestMatch,
        });
    }

    return function _strategy(params: { listA: T[]; listB: T[] }) {
        params = params || {};
        const listA = params.listA;
        const listB = params.listB;
        let indexA = 0;
        let indexB;

        let bestMatch = {
            score: 0.0,
            index: -1,
        };

        const paired = [];
        while (indexA < listA.length) {
            const matchTo = listA[indexA];
            bestMatch.score = 0.0;

            if (!matchTo) {
                continue;
            }
            for (indexB = 0; indexB < listB.length; indexB++) {
                const possible = listB[indexB] as T;
                if (listA[indexA] !== listB[indexB]) {
                    bestMatch = match(
                        _preprocessMatch({
                            matchTo: matchTo,
                            possible: possible,
                            index: indexB,
                            bestMatch: bestMatch,
                        })
                    );
                    if (bestMatch.score === 1.0) {
                        break;
                    }
                }
            }
            if (bestMatch.score >= scoreThreshold) {
                const createdPair = splicePairOutOfSuppliedLists({
                    listA: listA,
                    indexA: indexA,
                    listB: listB,
                    indexB: bestMatch.index,
                });
                if (createdPair) {
                    paired.push(createdPair);
                }
            } else {
                indexA += 1;
            }
            if (!listA.length || !listB.length) {
                return paired;
            }
        }
        return paired;
    };
}
