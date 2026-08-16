import { parse, stringify } from "yaml";

/**
 * Parse and serialize the content of a fenced config block (```visualization,
 * ```vega, ...).
 *
 * Blocks are authored as YAML, which is a superset of JSON: pasted Vega or
 * Vitessce specs (JSON) parse unchanged, while hand-written blocks get YAML's
 * plain-text ergonomics. Serialization emits YAML and preserves author key order.
 */
export function parseBlockContent(content: string): Record<string, unknown> {
    return (parse(content) ?? {}) as Record<string, unknown>;
}

export function serializeBlockContent(value: Record<string, unknown>): string {
    return stringify(value);
}
