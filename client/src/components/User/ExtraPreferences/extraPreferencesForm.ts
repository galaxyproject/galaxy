import type { components } from "@/api/schema";
import type { FormData, FormInputNode } from "@/components/Form/composables/useFormState";

export type ExtraPreferenceSection = components["schemas"]["ExtraPreferenceSectionDefinition"];
export type ExtraPreferenceInput = components["schemas"]["ExtraPreferenceInputDefinition"];
export type ExtraPreferenceValues = components["schemas"]["UserExtraPreferences"];
export type ExtraPreferencesPayload = components["schemas"]["UserExtraPreferencesUpdatePayload"];

type SecretState = components["schemas"]["ExtraPreferenceSecretState"];

export const STORED_SECRET_HINT = "A value is stored. Leave this empty to keep it.";

const SENSITIVE_KINDS = new Set(["password", "secret"]);

// structuredClone rejects the reactive proxies the page passes in
function clone<T>(value: T): T {
    return JSON.parse(JSON.stringify(value));
}

/** The input type as the server resolves it: an untyped input with options is a select. */
function inputKind(input: ExtraPreferenceInput): string {
    return input.type || (input.options?.length ? "select" : "text");
}

function isSensitive(input: ExtraPreferenceInput): boolean {
    return SENSITIVE_KINDS.has(inputKind(input));
}

function isSecretState(value: unknown): value is SecretState {
    return typeof value === "object" && value !== null && !Array.isArray(value) && "is_set" in value;
}

function isStored(values: ExtraPreferenceValues, section: string, input: ExtraPreferenceInput): boolean {
    const value = values[section]?.[input.name];
    return isSecretState(value) && value.is_set;
}

/** Key of an input in the flat form data the form emits. */
export function formKey(section: string, input: string): string {
    return `${section}|${input}`;
}

function emptyValue(input: ExtraPreferenceInput): FormData[string] {
    if (input.multiple) {
        return [];
    }
    switch (inputKind(input)) {
        case "boolean":
            return false;
        case "integer":
        case "float":
        case "select":
            return null;
        default:
            return "";
    }
}

function initialValue(values: ExtraPreferenceValues, section: string, input: ExtraPreferenceInput): FormData[string] {
    const stored = values[section]?.[input.name];
    if (stored !== undefined && stored !== null && !isSecretState(stored)) {
        return clone(stored);
    }
    return clone(input.value ?? emptyValue(input));
}

function buildInput(values: ExtraPreferenceValues, section: string, input: ExtraPreferenceInput): FormInputNode {
    const kind = inputKind(input);
    const { options, ...rest } = clone(input);
    const node: FormInputNode & Record<string, unknown> = {
        ...rest,
        ...(options ? { options } : {}),
        name: input.name,
        label: input.label || input.name,
        type: isSensitive(input) ? "password" : kind,
        help: input.help,
        optional: !input.required,
        value: initialValue(values, section, input),
    };
    if (isSensitive(input)) {
        // A stored secret is kept when the field is left empty, so only an unset required one is required.
        const stored = isStored(values, section, input);
        node.value = "";
        node.optional = !input.required || stored;
        node.help = [input.help, stored ? STORED_SECRET_HINT : ""].filter(Boolean).join(" ");
    }
    return node;
}

/** One form section per definition section; the form emits its values keyed by `formKey`. */
export function buildInputs(definition: ExtraPreferenceSection[], values: ExtraPreferenceValues): FormInputNode[] {
    return definition.map((section) => ({
        type: "section",
        name: section.name,
        title: section.description,
        expanded: true,
        inputs: (section.inputs ?? []).map((input) => buildInput(values, section.name, input)),
    }));
}

/** A required secret that is not stored and has no value typed in, which cannot be saved. */
export function isSecretMissing(
    definition: ExtraPreferenceSection[],
    values: ExtraPreferenceValues,
    formData: FormData,
): boolean {
    return definition.some((section) =>
        (section.inputs ?? []).some(
            (input) =>
                isSensitive(input) &&
                input.required &&
                !isStored(values, section.name, input) &&
                !formData[formKey(section.name, input.name)],
        ),
    );
}

/** The form widgets hand back strings for numbers, so values are put into the type the server checks. */
function normalize(input: ExtraPreferenceInput, raw: unknown): FormData[string] {
    if (raw === null || raw === undefined || raw === "" || (Array.isArray(raw) && raw.length === 0)) {
        return null;
    }
    switch (inputKind(input)) {
        case "boolean":
            return typeof raw === "string" ? raw.toLowerCase() === "true" : Boolean(raw);
        case "integer":
        case "float": {
            const number = Number(raw);
            // Left as it is, so the server names the invalid input.
            return Number.isNaN(number) ? raw : number;
        }
        default:
            return typeof raw === "string" && !input.multiple ? raw.trim() || null : raw;
    }
}

/**
 * What the server holds for an input. An unset input with a definition default is null, not the default,
 * so saving the displayed default stores it; one without a default is compared with its empty form value.
 */
function storedValue(values: ExtraPreferenceValues, section: string, input: ExtraPreferenceInput): FormData[string] {
    const stored = values[section]?.[input.name];
    if (stored !== undefined && stored !== null && !isSecretState(stored)) {
        return normalize(input, stored);
    }
    return input.value === undefined || input.value === null ? normalize(input, emptyValue(input)) : null;
}

/** The value the form displays for an input when it loads; a secret field always starts empty. */
function displayedValue(values: ExtraPreferenceValues, section: string, input: ExtraPreferenceInput): FormData[string] {
    return isSensitive(input) ? "" : normalize(input, initialValue(values, section, input));
}

/** Whether the current form value of an input is not what the form displayed on load. */
function isEdited(
    values: ExtraPreferenceValues,
    section: string,
    input: ExtraPreferenceInput,
    raw: FormData[string],
): boolean {
    if (isSensitive(input)) {
        return typeof raw === "string" && raw !== "";
    }
    return JSON.stringify(normalize(input, raw)) !== JSON.stringify(displayedValue(values, section, input));
}

/** The sections with an input the user changed, which is not the same as one that differs from what is stored. */
export function dirtySections(
    definition: ExtraPreferenceSection[],
    values: ExtraPreferenceValues,
    formData: FormData,
): Set<string> {
    const dirty = new Set<string>();
    for (const section of definition) {
        const edited = (section.inputs ?? []).some((input) => {
            const raw = formData[formKey(section.name, input.name)];
            return raw !== undefined && isEdited(values, section.name, input, raw);
        });
        if (edited) {
            dirty.add(section.name);
        }
    }
    return dirty;
}

/**
 * The values to PUT: in the sections the user edited, the inputs that differ from what is stored, so a default
 * shown there is stored with the edit. Untouched sections send nothing and keep their stored values.
 */
export function buildPayload(
    definition: ExtraPreferenceSection[],
    values: ExtraPreferenceValues,
    formData: FormData,
): ExtraPreferencesPayload {
    const payload: ExtraPreferencesPayload = {};
    const dirty = dirtySections(definition, values, formData);
    for (const section of definition) {
        if (!dirty.has(section.name)) {
            continue;
        }
        for (const input of section.inputs ?? []) {
            const raw = formData[formKey(section.name, input.name)];
            if (raw === undefined) {
                continue;
            }
            let value: FormData[string];
            if (isSensitive(input)) {
                // An empty field keeps the stored secret; a typed value is sent as it is.
                if (typeof raw !== "string" || raw === "") {
                    continue;
                }
                value = raw;
            } else {
                value = normalize(input, raw);
                if (JSON.stringify(value) === JSON.stringify(storedValue(values, section.name, input))) {
                    continue;
                }
            }
            (payload[section.name] ??= {})[input.name] = value;
        }
    }
    return payload;
}

export interface ClearableSecret {
    section: string;
    sectionLabel: string;
    name: string;
    label: string;
}

/** Stored secrets that may be cleared; the server refuses to clear a required one. */
export function clearableSecrets(
    definition: ExtraPreferenceSection[],
    values: ExtraPreferenceValues,
): ClearableSecret[] {
    return definition.flatMap((section) =>
        (section.inputs ?? [])
            .filter((input) => isSensitive(input) && !input.required && isStored(values, section.name, input))
            .map((input) => ({
                section: section.name,
                sectionLabel: section.description,
                name: input.name,
                label: input.label || input.name,
            })),
    );
}

export function buildClearPayload(section: string, name: string): ExtraPreferencesPayload {
    return { [section]: { [name]: null } };
}
