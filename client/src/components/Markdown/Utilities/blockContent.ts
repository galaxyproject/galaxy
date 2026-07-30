import { stringify } from "./stringify";

/**
 * Parse and serialize the content of a fenced config block (```visualization,
 * ```vega, ...).
 *
 * This is the single seam for the block serialization format. Today it is JSON;
 * a YAML-superset parser will be swapped in here without touching every consumer.
 * Valid JSON is valid YAML, so pasted Vega/Vitessce specs keep parsing unchanged.
 */
export function parseBlockContent(content: string): Record<string, unknown> {
    return JSON.parse(content);
}

export function serializeBlockContent(value: Record<string, unknown>): string {
    return stringify(value);
}
