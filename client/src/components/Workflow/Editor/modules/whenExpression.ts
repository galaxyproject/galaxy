/**
 * Static analysis of workflow step `when` expressions.
 *
 * Galaxy addresses connected tool inputs by flat, pipe-prefixed connection names
 * (`cond|input1`), while a `when` expression walks nested tool state
 * (`inputs.cond.input1`). These helpers bridge the two representations so the editor can
 * reason about which inputs a gate reads and how the gate behaves when one of them is
 * absent.
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

export type NullBehavior = "false-when-null" | "true-when-null" | "unknown";

const PUNCTUATORS = ["===", "!==", "==", "!=", "&&", "||", "!", "(", ")", "[", "]", ".", ",", "?", ":"];

// `UNKNOWN` has unknown value and truthiness. The other two retain only the
// truthiness established by short-circuit evaluation; equality must still treat their
// exact values as indeterminate.
const UNKNOWN = Symbol("unknown");
const TRUTHY_UNKNOWN = Symbol("truthy-unknown");
const FALSY_UNKNOWN = Symbol("falsy-unknown");

type EvaluatedValue =
    | typeof UNKNOWN
    | typeof TRUTHY_UNKNOWN
    | typeof FALSY_UNKNOWN
    | string
    | number
    | boolean
    | null
    | undefined;

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

function isSamePath(targetPath: InputPath, referencedPath: InputPath): boolean {
    return targetPath.length === referencedPath.length && inputPathIsPrefix(targetPath, referencedPath);
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

/**
 * Decide how the expression behaves when the named connection carries no value.
 *
 * Evaluates a small, side-effect-free subset of JavaScript — literals, `inputs`
 * accesses, `!`, equality, and `&&`/`||` — with the target bound to `null` and every
 * other input left indeterminate. Anything outside that subset is `"unknown"`.
 */
export function classifyWhenInputIsNull(
    expression: string | null | undefined,
    input: string | readonly InputPathSegment[],
): NullBehavior {
    if (!expression) {
        return "unknown";
    }

    const trimmed = expression.trim();
    if (isTemplateLiteral(trimmed)) {
        return "unknown";
    }

    const tokens = tokenize(trimmed);
    // Galaxy `when` expressions are a `$(...)` body.
    if (!tokens || tokens[0]?.value !== "$" || tokens[1]?.value !== "(") {
        return "unknown";
    }

    const parser = new PresenceEvaluator(tokens, normalizeInputPath(input));
    const value = parser.evaluate();
    if (value === UNKNOWN) {
        return "unknown";
    }

    return isTruthy(value) ? "true-when-null" : "false-when-null";
}

/**
 * True when the editor should treat the expression as a presence guard for the input.
 *
 * This is deliberately permissive for existing, hand-written expressions: a gate that
 * references the input is accepted unless the evaluator can prove it runs while the
 * input is absent. The runtime remains authoritative for expressions classified as
 * unknown.
 */
export function expressionGuardsInputPresence(
    expression: string | null | undefined,
    input: string | readonly InputPathSegment[],
): boolean {
    if (!expressionReferencesInput(expression, input)) {
        return false;
    }

    return classifyWhenInputIsNull(expression, input) !== "true-when-null";
}

function isTruthy(value: Exclude<EvaluatedValue, typeof UNKNOWN>): boolean {
    if (value === TRUTHY_UNKNOWN) {
        return true;
    }
    if (value === FALSY_UNKNOWN) {
        return false;
    }
    return Boolean(value);
}

/** Raised on anything the evaluator does not model; mapped to "unknown", never to a verdict. */
class ParseFailure extends Error {}

/** Recursive-descent evaluator over the recognized expression subset. */
class PresenceEvaluator {
    private tokens: Token[];
    private targetPath: InputPath;
    private position: number;

    constructor(tokens: Token[], targetPath: InputPath) {
        this.tokens = tokens;
        this.targetPath = targetPath;
        this.position = 2;
    }

    evaluate(): EvaluatedValue {
        try {
            const value = this.parseOr();
            if (!this.consume(")") || !this.atEnd()) {
                return UNKNOWN;
            }
            return value;
        } catch {
            // Including anything the recursive descent itself can raise, such as a
            // RangeError on a deeply nested expression. Nothing escapes into the editor.
            return UNKNOWN;
        }
    }

    /** Only statement punctuation may follow the expression body. */
    private atEnd(): boolean {
        return this.tokens.slice(this.position).every((token) => token.value === ";");
    }

    private peek(): Token | undefined {
        return this.tokens[this.position];
    }

    private consume(value: string): boolean {
        if (this.peek()?.value === value) {
            this.position++;
            return true;
        }
        return false;
    }

    private parseOr(): EvaluatedValue {
        let left = this.parseAnd();
        while (this.consume("||")) {
            const right = this.parseAnd();
            left = combineOr(left, right);
        }
        return left;
    }

    private parseAnd(): EvaluatedValue {
        let left = this.parseEquality();
        while (this.consume("&&")) {
            const right = this.parseEquality();
            left = combineAnd(left, right);
        }
        return left;
    }

    private parseEquality(): EvaluatedValue {
        let left = this.parseUnary();
        for (;;) {
            const operator = this.peek()?.value;
            if (operator !== "===" && operator !== "!==" && operator !== "==" && operator !== "!=") {
                return left;
            }
            this.position++;
            const right = this.parseUnary();
            left = compare(operator, left, right);
        }
    }

    private parseUnary(): EvaluatedValue {
        if (this.consume("!")) {
            const value = this.parseUnary();
            return value === UNKNOWN ? UNKNOWN : !isTruthy(value);
        }
        return this.parsePrimary();
    }

    private parsePrimary(): EvaluatedValue {
        const token = this.peek();
        if (!token) {
            throw new ParseFailure("unexpected end of expression");
        }

        if (this.consume("(")) {
            const value = this.parseOr();
            if (!this.consume(")")) {
                throw new ParseFailure("unbalanced parentheses");
            }
            return value;
        }

        if (token.type === "string") {
            this.position++;
            return token.value;
        }

        if (token.type === "number") {
            this.position++;
            return Number(token.value);
        }

        if (token.type === "identifier") {
            return this.parseIdentifier(token);
        }

        throw new ParseFailure(`unrecognized token ${token.value}`);
    }

    private parseIdentifier(token: Token): EvaluatedValue {
        this.position++;

        switch (token.value) {
            case "null":
                return null;
            case "undefined":
                return undefined;
            case "true":
                return true;
            case "false":
                return false;
        }

        if (token.value !== "inputs") {
            throw new ParseFailure(`unrecognized identifier ${token.value}`);
        }

        const path = readAccessPath(this.tokens, this.position);
        this.position = path.next;
        if (path.dynamic) {
            throw new ParseFailure("dynamic inputs access");
        }
        // Only the target itself is known to be null. Reading a property *of* the target
        // would throw at run time rather than yield a value, so it stays indeterminate.
        if (isSamePath(this.targetPath, path.segments)) {
            return null;
        }
        if (
            inputPathIsPrefix(this.targetPath, path.segments) &&
            path.optionalAfterSegments.includes(this.targetPath.length)
        ) {
            // `target?.property` short-circuits to undefined when target is null;
            // the equivalent non-optional property read throws and remains unknown.
            return undefined;
        }
        return UNKNOWN;
    }
}

function combineAnd(left: EvaluatedValue, right: EvaluatedValue): EvaluatedValue {
    if (left === UNKNOWN) {
        // If the unknown left side is falsy, JavaScript returns that falsy value;
        // otherwise it returns `right`. A falsy right therefore settles the result's
        // truthiness even though its exact value is unknown.
        return right !== UNKNOWN && !isTruthy(right) ? FALSY_UNKNOWN : UNKNOWN;
    }
    return isTruthy(left) ? right : left;
}

function combineOr(left: EvaluatedValue, right: EvaluatedValue): EvaluatedValue {
    if (left === UNKNOWN) {
        // Symmetrically, a truthy right side makes `unknown || right` truthy for
        // either possible truthiness of the left side.
        return right !== UNKNOWN && isTruthy(right) ? TRUTHY_UNKNOWN : UNKNOWN;
    }
    return isTruthy(left) ? left : right;
}

function compare(operator: string, left: EvaluatedValue, right: EvaluatedValue): EvaluatedValue {
    if (isIndeterminate(left) || isIndeterminate(right)) {
        return UNKNOWN;
    }

    const strict = left === right;
    if (operator === "===") {
        return strict;
    }
    if (operator === "!==") {
        return !strict;
    }

    // Loose equality across types has its own coercion rules -- `1 == "1"` is true.
    // Decide it only where coercion cannot apply.
    let loose: boolean;
    if (isNullish(left) || isNullish(right)) {
        loose = isNullish(left) && isNullish(right);
    } else if (typeof left === typeof right) {
        loose = strict;
    } else {
        return UNKNOWN;
    }

    return operator === "==" ? loose : !loose;
}

function isNullish(value: Exclude<EvaluatedValue, typeof UNKNOWN>): boolean {
    return value === null || value === undefined;
}

function isIndeterminate(
    value: EvaluatedValue,
): value is typeof UNKNOWN | typeof TRUTHY_UNKNOWN | typeof FALSY_UNKNOWN {
    return value === UNKNOWN || value === TRUTHY_UNKNOWN || value === FALSY_UNKNOWN;
}

const JAVASCRIPT_IDENTIFIER = /^[A-Za-z_$][A-Za-z0-9_$]*$/;

function normalizeInputPath(input: string | readonly InputPathSegment[]): InputPath {
    return typeof input === "string" ? connectionNameToInputPath(input) : [...input];
}

/** Spell an input path as a JavaScript access path into `inputs`. */
export function inputsAccessPath(input: string | readonly InputPathSegment[]): string {
    return normalizeInputPath(input).reduce<string>((path, segment) => {
        if (typeof segment === "number") {
            return `${path}[${segment}]`;
        }
        return JAVASCRIPT_IDENTIFIER.test(segment) ? `${path}.${segment}` : `${path}[${JSON.stringify(segment)}]`;
    }, "inputs");
}

/** The `when` expression that runs a step only while the addressed input carries a value. */
export function presenceGateExpression(input: string | readonly InputPathSegment[]): string {
    return `$(${inputsAccessPath(input)} !== null)`;
}

/** The established workflow-editor convention for a direct boolean gate. */
export const BOOLEAN_GATE_INPUT_NAME = "when";
export const BOOLEAN_GATE_EXPRESSION = `$(inputs.${BOOLEAN_GATE_INPUT_NAME})`;
