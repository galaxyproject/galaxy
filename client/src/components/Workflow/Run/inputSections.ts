/** A collapsible group of workflow inputs, as defined in the workflow's `input_sections`. */
export interface WorkflowInputSection {
    name: string;
    label?: string | null;
    expanded?: boolean;
    help?: string | null;
}

interface GroupableInput {
    name: unknown;
    optional?: boolean;
    value?: unknown;
}

export interface SectionFormInput<T> {
    type: "section";
    name: string;
    title: string;
    expanded: boolean;
    help?: string | null;
    inputs: T[];
}

function needsValue(input: GroupableInput): boolean {
    if (input.optional) {
        return false;
    }
    const value = input.value;
    if (value === undefined || value === null || value === "") {
        return true;
    }
    if (typeof value === "object" && "values" in value) {
        const values = (value as { values?: unknown[] }).values;
        return !values || values.length === 0;
    }
    return false;
}

/**
 * Group run form inputs into the `section` inputs FormDisplay renders for tool sections.
 *
 * Inputs keep their order. A section is placed where its first member is, and is open
 * when the workflow says so or when it holds a required input that has no value yet.
 * Inputs assigned to a section without a definition are grouped under the section name.
 */
export function groupInputsIntoSections<T extends GroupableInput>(
    inputs: T[],
    sections: WorkflowInputSection[],
    sectionOf: Map<string, string>,
): Array<T | SectionFormInput<T>> {
    if (sectionOf.size === 0) {
        return inputs;
    }
    const definitions = new Map(sections.map((section) => [section.name, section]));
    const grouped: Array<T | SectionFormInput<T>> = [];
    const placed = new Map<string, SectionFormInput<T>>();
    for (const input of inputs) {
        const sectionName = sectionOf.get(String(input.name));
        if (!sectionName) {
            grouped.push(input);
            continue;
        }
        let sectionInput = placed.get(sectionName);
        if (!sectionInput) {
            const definition = definitions.get(sectionName);
            sectionInput = {
                type: "section",
                name: sectionName,
                title: definition?.label || sectionName,
                expanded: Boolean(definition?.expanded),
                help: definition?.help,
                inputs: [],
            };
            placed.set(sectionName, sectionInput);
            grouped.push(sectionInput);
        }
        sectionInput.inputs.push(input);
        if (needsValue(input)) {
            sectionInput.expanded = true;
        }
    }
    return grouped;
}

/** Strip the `<section>|` prefix FormDisplay adds to the names of inputs inside a section. */
export function stripSectionPrefix(name: string, sectionNames: Iterable<string>): string {
    for (const sectionName of sectionNames) {
        const prefix = `${sectionName}|`;
        if (name.startsWith(prefix)) {
            return name.slice(prefix.length);
        }
    }
    return name;
}

/** Key FormDisplay values by input name again, dropping section prefixes. */
export function flattenSectionedValues<V>(
    values: Record<string, V>,
    sectionNames: Iterable<string>,
): Record<string, V> {
    const names = [...sectionNames];
    if (names.length === 0) {
        return values;
    }
    const flat: Record<string, V> = {};
    for (const [key, value] of Object.entries(values)) {
        flat[stripSectionPrefix(key, names)] = value;
    }
    return flat;
}
