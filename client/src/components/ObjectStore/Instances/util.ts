import { markup } from "@/components/ObjectStore/configurationMarkdown";

import type { ObjectStoreTemplateSecret, ObjectStoreTemplateVariable, VariableValueType } from "./types";

export function metadataFormEntryName() {
    return {
        name: "_meta_name",
        label: "Name",
        type: "text",
        optional: false,
        help: "Label this new object store a name.",
    };
}

export function metadataFormEntryDescription() {
    return {
        name: "_meta_description",
        label: "Description",
        optional: true,
        type: "textarea",
        help: "Provide some notes to yourself about this object store - perhaps to remind you how it is configured, where it stores the data, etc..",
    };
}

export function templateVariableFormEntry(variable: ObjectStoreTemplateVariable, variableValue: VariableValueType) {
    return {
        name: variable.name,
        type: "text",
        help: markup(variable.help || "", true),
        value: variableValue,
    };
}

export function templateSecretFormEntry(secret: ObjectStoreTemplateSecret) {
    return {
        name: secret.name,
        type: "password",
        help: markup(secret.help || "", true),
        value: "",
    };
}

export function asNumber(x: number | string): number {
    return +x;
}
