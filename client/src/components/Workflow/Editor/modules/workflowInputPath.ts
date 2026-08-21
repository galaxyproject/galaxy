/**
 * Translate between persisted workflow connection names and `when` input paths.
 *
 * Galaxy flattens nested tool inputs with `|` in `input_connections`, while expression
 * code addresses the same input one property at a time. Keep comparisons segmented:
 * joining an expression path is lossy when a literal property name itself contains `|`.
 */

export type InputPathSegment = string | number;
export type InputPath = InputPathSegment[];

/** Map a flat, pipe-delimited connection name onto its ordinary nested `inputs` path. */
export function connectionNameToInputPath(inputName: string): InputPath {
    return inputName.split("|");
}

/**
 * Resolve a flattened connection name against tool state, including repeat indices.
 *
 * A repeat named `queries` produces connection names such as `queries_0|input2`, but
 * expression state exposes that value as `inputs.queries[0].input2`. Exact property
 * names win only when they are the sole successful interpretation; if both a literal
 * `queries_0` group and the repeat path resolve, declining is safer than gating on the
 * wrong value.
 */
export function resolveConnectionNameToInputPath(
    inputName: string,
    rawToolState: Record<string, unknown> | null | undefined,
): InputPath | null {
    if (!inputName.includes("|")) {
        // Top-level workflow-only probes are not represented in tool state.
        return [inputName];
    }

    const state = parseTopLevelToolState(rawToolState ?? {});
    const resolutions = resolveSegments(inputName.split("|"), 0, state);
    return resolutions.length === 1 ? resolutions[0]! : null;
}

function resolveSegments(segments: string[], position: number, level: unknown): InputPath[] {
    if (position === segments.length) {
        return [[]];
    }
    if (!isRecord(level)) {
        return [];
    }

    const segment = segments[position]!;
    const candidates: Array<{ path: InputPath; value: unknown }> = [];
    if (Object.prototype.hasOwnProperty.call(level, segment)) {
        candidates.push({ path: [segment], value: level[segment] });
    }

    const repeat = /^(.*)_([0-9]+)$/.exec(segment);
    if (repeat) {
        const [, repeatName, indexText] = repeat;
        const repeatValue = level[repeatName!];
        const index = Number(indexText);
        if (Array.isArray(repeatValue) && index in repeatValue) {
            candidates.push({ path: [repeatName!, index], value: repeatValue[index] });
        }
    }

    return candidates.flatMap(({ path, value }) =>
        resolveSegments(segments, position + 1, value).map((suffix) => [...path, ...suffix]),
    );
}

/** Tool state arrives with its top-level values JSON encoded, inconsistently. */
function parseTopLevelToolState(raw: Record<string, unknown>): Record<string, unknown> {
    return Object.fromEntries(
        Object.entries(raw).map(([key, value]) => [key, typeof value === "string" ? tryParseJson(value) : value]),
    );
}

function tryParseJson(value: string): unknown {
    try {
        return JSON.parse(value);
    } catch {
        return value;
    }
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** True when `targetPath` names `referencedPath` or one of its ancestors. */
export function inputPathIsPrefix(
    targetPath: readonly InputPathSegment[],
    referencedPath: readonly InputPathSegment[],
): boolean {
    if (targetPath.length > referencedPath.length) {
        return false;
    }
    return targetPath.every((segment, position) => segment === referencedPath[position]);
}
