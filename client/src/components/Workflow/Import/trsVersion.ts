/** Parse a TRS version name like "v1.2.3" into numeric parts, or null if it holds no version number. */
function parseTrsVersion(name: string): number[] | null {
    const match = name.match(/(\d+)(?:\.(\d+))?(?:\.(\d+))?/);
    if (!match) {
        return null;
    }
    return [
        parseInt(match[1] as string, 10),
        match[2] !== undefined ? parseInt(match[2], 10) : 0,
        match[3] !== undefined ? parseInt(match[3], 10) : 0,
    ];
}

/** Whether a TRS version name carries a version number, as opposed to e.g. a branch name. */
export function isTrsVersion(name: string): boolean {
    return parseTrsVersion(name) !== null;
}

/** Compare two TRS version names in ascending order; null when either isn't a version, e.g. a branch name. */
export function compareTrsVersions(left: string, right: string): number | null {
    const a = parseTrsVersion(left);
    const b = parseTrsVersion(right);
    if (!a || !b) {
        return null;
    }
    for (let i = 0; i < 3; i++) {
        if (a[i] !== b[i]) {
            return (a[i] as number) - (b[i] as number);
        }
    }
    return 0;
}
