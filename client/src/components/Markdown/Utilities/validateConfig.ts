import Ajv2020, { type ErrorObject } from "ajv/dist/2020";

/**
 * Validate a parsed embed config against a visualization's JSON Schema
 * (served as `parameters_schema` on the plugin). Returns human-readable warning
 * strings; an empty array means no problems. Never throws: authoring is never
 * blocked, so a schema that fails to compile yields no warnings.
 */

const ajv = new Ajv2020({ allErrors: true, strict: false });

// Union/branch keywords whose failures are noise once the leaf error is reported.
const WRAPPER_KEYWORDS = new Set(["anyOf", "oneOf", "if", "not"]);

export function validateConfig(schema: Record<string, unknown>, config: unknown): string[] {
    let validate;
    try {
        validate = ajv.compile(schema);
    } catch {
        return [];
    }
    if (validate(config)) {
        return [];
    }
    return formatErrors(validate.errors ?? []);
}

function formatPath(instancePath: string): string {
    const cleaned = instancePath.replace(/^\//, "").replace(/\//g, ".");
    return cleaned || "(root)";
}

function formatErrors(errors: ErrorObject[]): string[] {
    // A discriminated union (conditional) emits one `const` failure per case; collect
    // the allowed discriminator values per path so they read as a single choice list.
    const constValues = new Map<string, Set<string>>();
    for (const error of errors) {
        if (error.keyword === "const") {
            const values = constValues.get(error.instancePath) ?? new Set<string>();
            values.add(String((error.params as { allowedValue: unknown }).allowedValue));
            constValues.set(error.instancePath, values);
        }
    }

    const messages = new Set<string>();
    for (const error of errors) {
        if (WRAPPER_KEYWORDS.has(error.keyword) || error.message === "must be null") {
            continue;
        }
        const path = formatPath(error.instancePath);
        if (error.keyword === "const") {
            const values = [...(constValues.get(error.instancePath) ?? [])];
            messages.add(`${path}: must be one of: ${values.join(", ")}`);
        } else if (error.keyword === "enum") {
            const values = (error.params as { allowedValues?: unknown[] }).allowedValues ?? [];
            messages.add(`${path}: must be one of: ${values.join(", ")}`);
        } else if (error.keyword === "additionalProperties") {
            const property = (error.params as { additionalProperty: string }).additionalProperty;
            messages.add(`${path}: unexpected property "${property}"`);
        } else {
            messages.add(`${path}: ${error.message}`);
        }
    }
    return [...messages];
}
