/**
 * Static analysis of workflow step `when` expressions.
 *
 * Galaxy addresses connected tool inputs by flat, pipe-prefixed connection names
 * (`cond|input1`), while a `when` expression walks nested tool state
 * (`inputs.cond.input1`). These helpers bridge the two representations so the editor can
 * reason about which inputs an expression reads.
 *
 * Nothing here executes user JavaScript. Expressions that are not structurally
 * recognized are reported as unknown, and callers are expected to resolve unknown
 * permissively: the runtime, not the editor, decides whether a step runs.
 */

import {
    connectionNameToInputPath,
    type InputPath,
    inputPathIsPrefix,
    type InputPathSegment,
} from "./workflowInputPath";

type TokenType = "identifier" | "number" | "string" | "punct";

interface Token {
    type: TokenType;
    value: string;
}

export interface ReferenceAnalysis {
    /** Fully static `inputs` accesses, as path segments. */
    staticPaths: InputPath[];
    /** True when some `inputs` access could not be resolved statically. */
    hasDynamicInputsAccess: boolean;
}

const PUNCTUATORS = ["===", "!==", "==", "!=", "&&", "||", "!", "(", ")", "[", "]", ".", ",", "?", ":"];

/** Tokenize a JavaScript-ish expression, or return null when it cannot be scanned. */
function tokenize(expression: string): Token[] | null {
    const tokens: Token[] = [];
    let index = 0;

    while (index < expression.length) {
        const char = expression[index]!;

        if (/\s/.test(char)) {
            index++;
            continue;
        }

        if (char === "/" && expression[index + 1] === "/") {
            const newline = expression.indexOf("\n", index);
            index = newline === -1 ? expression.length : newline;
            continue;
        }

        if (char === "/" && expression[index + 1] === "*") {
            const end = expression.indexOf("*/", index + 2);
            if (end === -1) {
                return null;
            }
            index = end + 2;
            continue;
        }

        if (char === "/") {
            // Ignore regex contents so text such as `inputs.foo` inside the pattern is
            // not mistaken for an access. If this slash follows a value, it may instead
            // be division; leave that unsupported rather than guessing.
            if (!canStartRegex(tokens)) {
                return null;
            }
            const next = readRegexLiteral(expression, index);
            if (next === null) {
                return null;
            }
            index = next;
            continue;
        }

        if (char === '"' || char === "'" || char === "`") {
            const literal = readStringLiteral(expression, index);
            if (!literal) {
                return null;
            }
            tokens.push({ type: "string", value: literal.value });
            index = literal.next;
            continue;
        }

        if (/[0-9]/.test(char)) {
            const match = /^[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?/.exec(expression.slice(index))!;
            tokens.push({ type: "number", value: match[0] });
            index += match[0].length;
            continue;
        }

        if (/[A-Za-z_$]/.test(char)) {
            const match = /^[A-Za-z_$][A-Za-z0-9_$]*/.exec(expression.slice(index))!;
            tokens.push({ type: "identifier", value: match[0] });
            index += match[0].length;
            continue;
        }

        const punctuator = PUNCTUATORS.find((candidate) => expression.startsWith(candidate, index));
        tokens.push({ type: "punct", value: punctuator ?? char });
        index += punctuator?.length ?? 1;
    }

    return tokens;
}

/** Conservatively recognize regex literals where the analyzer's subset expects a value. */
function canStartRegex(tokens: Token[]): boolean {
    const previous = tokens[tokens.length - 1];
    if (!previous) {
        return true;
    }
    return previous.type === "punct" && previous.value !== ")" && previous.value !== "]" && previous.value !== ".";
}

/** Skip a regex literal, including escaped characters, character classes, and flags. */
function readRegexLiteral(expression: string, start: number): number | null {
    let index = start + 1;
    let inCharacterClass = false;

    while (index < expression.length) {
        const char = expression[index]!;
        if (char === "\\") {
            index += 2;
            continue;
        }
        if (char === "[") {
            inCharacterClass = true;
        } else if (char === "]") {
            inCharacterClass = false;
        } else if (char === "/" && !inCharacterClass) {
            index++;
            while (/[A-Za-z]/.test(expression[index] ?? "")) {
                index++;
            }
            return index;
        } else if (char === "\n" || char === "\r") {
            return null;
        }
        index++;
    }

    return null;
}

/** Read a quoted literal starting at `start`. Template literals keep their raw body. */
function readStringLiteral(expression: string, start: number): { value: string; next: number } | null {
    const quote = expression[start]!;
    let value = "";
    let index = start + 1;

    while (index < expression.length) {
        const char = expression[index]!;
        if (char === "\\") {
            value += expression[index + 1] ?? "";
            index += 2;
            continue;
        }
        if (char === quote) {
            return { value, next: index + 1 };
        }
        value += char;
        index++;
    }

    return null;
}

function isTemplateLiteral(expression: string): boolean {
    return expression.includes("`");
}

/**
 * Collect every `inputs` access in an expression.
 *
 * Recognizes dot access, chained bracket access with string or numeric literals, and
 * mixtures of the two. Anything else — a computed index, a bare `inputs` reference, a template
 * literal that might interpolate one — is reported through `hasDynamicInputsAccess`.
 */
export function analyzeInputReferences(expression: string): ReferenceAnalysis {
    const tokens = tokenize(expression);
    if (!tokens) {
        return { staticPaths: [], hasDynamicInputsAccess: true };
    }

    const analysis: ReferenceAnalysis = {
        staticPaths: [],
        hasDynamicInputsAccess: isTemplateLiteral(expression),
    };

    tokens.forEach((token, position) => {
        if (token.type !== "identifier" || token.value !== "inputs") {
            return;
        }
        if (tokens[position - 1]?.value === ".") {
            return;
        }
        const path = readAccessPath(tokens, position + 1);
        if (path.dynamic || path.segments.length === 0) {
            analysis.hasDynamicInputsAccess = true;
        }
        if (path.segments.length > 0) {
            analysis.staticPaths.push(path.segments);
        }
    });

    return analysis;
}

interface AccessPath {
    segments: InputPath;
    /** Segment counts after which `?.` starts an optional chain. */
    optionalAfterSegments: number[];
    dynamic: boolean;
    next: number;
}

/** Walk the property access chain that follows an `inputs` token. */
function readAccessPath(tokens: Token[], start: number): AccessPath {
    const segments: InputPath = [];
    const optionalAfterSegments: number[] = [];
    let index = start;

    for (;;) {
        if (tokens[index]?.value === "?" && (tokens[index + 1]?.value === "." || tokens[index + 1]?.value === "[")) {
            optionalAfterSegments.push(segments.length);
            // `value?.name` leaves the dot for the ordinary dot-access branch;
            // `value?.[name]` must skip both `?` and `.` to reach the bracket.
            index += tokens[index + 1]?.value === "." && tokens[index + 2]?.value === "[" ? 2 : 1;
        }
        const token = tokens[index];
        if (token?.value === "." && tokens[index + 1]?.type === "identifier") {
            segments.push(tokens[index + 1]!.value);
            index += 2;
            continue;
        }
        if (token?.value === "[") {
            const inner = tokens[index + 1];
            if ((inner?.type === "string" || inner?.type === "number") && tokens[index + 2]?.value === "]") {
                segments.push(inner.type === "number" ? Number(inner.value) : inner.value);
                index += 3;
                continue;
            }
            return { segments, optionalAfterSegments, dynamic: true, next: index };
        }
        return { segments, optionalAfterSegments, dynamic: false, next: index };
    }
}

/**
 * True when the expression could read the named connection.
 *
 * Deliberately permissive: an expression the analyzer cannot resolve is treated as
 * referencing every candidate. Callers only ever ask about inputs that are already
 * connected, so an over-match shows a real edge while an under-match hides one.
 */
export function expressionReferencesInput(
    expression: string | null | undefined,
    input: string | readonly InputPathSegment[],
): boolean {
    if (!expression) {
        return false;
    }

    const targetPath = normalizeInputPath(input);
    const references = analyzeInputReferences(expression);

    if (references.hasDynamicInputsAccess) {
        return true;
    }

    return references.staticPaths.some((referencedPath) => inputPathIsPrefix(targetPath, referencedPath));
}

function normalizeInputPath(input: string | readonly InputPathSegment[]): InputPath {
    return typeof input === "string" ? connectionNameToInputPath(input) : [...input];
}
