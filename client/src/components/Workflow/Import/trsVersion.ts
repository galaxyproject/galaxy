import type { TrsToolVersion } from "./types";

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
function isTrsVersion(name: string): boolean {
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

/** Version numbers first, newest at the top, then everything else (branches) by name. */
export function sortTrsVersions(versions: TrsToolVersion[]): TrsToolVersion[] {
    return versions.slice().sort((a, b) => {
        const comparison = compareTrsVersions(b.name, a.name);
        if (comparison !== null) {
            return comparison;
        }
        const aIsVersion = isTrsVersion(a.name);
        const bIsVersion = isTrsVersion(b.name);
        if (aIsVersion !== bIsVersion) {
            return aIsVersion ? -1 : 1;
        }
        return b.name.localeCompare(a.name);
    });
}

/** The id that addresses a version on the TRS server; Dockstore's version ids repeat the tool id. */
export function trsVersionId(version: TrsToolVersion): string {
    return version.id.includes(`:${version.name}`) ? version.name : version.id;
}
